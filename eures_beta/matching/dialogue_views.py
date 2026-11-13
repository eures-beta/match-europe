"""Private candidate dialogue, with explicit review before any write."""

from django import forms
import secrets
import time
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from . import confirmation_services as confirmations, dialogue_services as dialogue
from .confirmation_views import AnswerForm, entry_candidate, display_rows
from .services import StaleEvaluation
from eures_beta.users.views import selected_language
from eures_beta.candidates import registration
from eures_beta.candidates.journey import KEY, SCHEMA, SCHEDULE_PERIODS, MobilityForm


class ReplyForm(forms.Form):
    history_token = forms.CharField(
        max_length=16000, required=False, widget=forms.HiddenInput
    )
    key = forms.CharField(max_length=250, widget=forms.HiddenInput)
    fingerprint = forms.CharField(max_length=64, widget=forms.HiddenInput)
    context = forms.CharField(max_length=64, widget=forms.HiddenInput)
    previous = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    text = forms.CharField(
        label=_('Your reply'),
        max_length=2000,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text=_(
            'Describe work-related details only. Do not include sensitive personal information.'
        ),
    )
    scope = forms.ChoiceField(
        label=_('Does your reply concern this offer or your general profile?'),
        required=False,
        widget=forms.RadioSelect,
        choices=[('offer', _('This offer only')), ('profile', _('My general profile'))],
    )


class AcceptForm(forms.Form):
    token = forms.CharField(max_length=16000, widget=forms.HiddenInput)
    update_profile = forms.BooleanField(
        label=_('I confirm this change to my general profile'), required=False
    )


def question_order(row):
    kind = row['kind']
    if kind in {'schedule', 'availability', 'working_time', 'work_condition'}:
        group = 0
    elif kind in {'skill', 'skills', 'language', 'languages'}:
        group = 2
    else:
        group = 1
    expected = row['presented']['expected']
    mandatory = isinstance(expected, dict) and expected.get('mandatory')
    return group, not mandatory, row.get('priority', 1), kind != 'schedule'


def question_text(row):
    short = confirmations.short_question(row)
    if short:
        return str(short)
    requirement = row['expected']
    prompts = {
        'schedule': _('Can you work these hours: %(requirement)s?'),
        'availability': _(
            'Can you start within the timeframe stated in the offer: %(requirement)s?'
        ),
        'working_time': _('Would this working arrangement suit you: %(requirement)s?'),
        'work_condition': _(
            'The offer mentions this working condition: %(requirement)s. Would it suit you?'
        ),
        'mobility': _(
            'Can you get to the workplace under these conditions: %(requirement)s?'
        ),
        'contract': _('Would this type of contract suit you: %(requirement)s?'),
        'salary': _(
            'Does the pay stated in the offer meet your expectations: %(requirement)s?'
        ),
        'permit': _('Do you have the permit stated in the offer: %(requirement)s?'),
        'skill': _('Can you use this skill on the job: %(requirement)s?'),
        'language': _(
            'Can you work in the language and at the level stated: %(requirement)s?'
        ),
    }
    template = prompts.get(
        row['kind'], _('%(condition)s: %(requirement)s. Would that suit you?')
    )
    return str(template % {'condition': row['label'], 'requirement': requirement})


@entry_candidate
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def conversation(request, pk):
    if not dialogue.enabled():
        raise Http404
    obj = get_object_or_404(
        confirmations.candidate_requests(request.user).select_related(
            'pair__candidate', 'pair__offer'
        ),
        pk=pk,
    )
    language = selected_language(request)
    state = confirmations.review(obj)
    rows = display_rows(state['rows'], language)
    key = request.POST.get('key') or request.GET.get('question')
    current = (
        next((r for r in rows if r['key'] == key and r['askable']), None)
        if key
        else min(
            (row for row in rows if row['askable'] and not row['answer']),
            key=question_order,
            default=None,
        )
    )
    prompt = question_text(current) if current else ''
    rows_by_key = {row['key']: row for row in rows}
    answered = []
    for answer in obj.answers.order_by('pk'):
        row = rows_by_key.get(answer.question_key)
        saved_prompt = answer.dialogue.get('prompt')
        if not saved_prompt and (not row or row['answer'] != answer or row == current):
            continue
        label = {
            'yes': _('Yes'),
            'no': _('No'),
            'conditional': _('Under conditions'),
            'changed': _('My situation changed'),
            'clarify': _('More details needed'),
        }[answer.value]
        answered.append(
            {
                'answer': answer,
                'prompt': saved_prompt or question_text(row),
                'answer_label': label,
            }
        )
    proposal, error, status = None, '', 200
    clarification, turns = '', []
    form = ReplyForm(
        request.POST
        if request.method == 'POST' and request.POST.get('action') == 'reply'
        else None
    )
    if request.method == 'POST':
        try:
            if request.POST.get('action') == 'quick':
                quick = AnswerForm(request.POST)
                if (
                    not quick.is_valid()
                    or quick.cleaned_data['value'] not in ('yes', 'no')
                    or quick.cleaned_data['detail']
                ):
                    raise ValueError
                confirmations.answer(
                    request.user, pk, **quick.cleaned_data, dialogue={'prompt': prompt}
                )
                return redirect(
                    reverse('candidate_offer_dialogue', args=[pk])
                    + '?lang='
                    + language
                    + '#question-title'
                )
            if request.POST.get('action') == 'accept':
                accepted = AcceptForm(request.POST)
                if not accepted.is_valid():
                    raise ValueError
                payload = signing.loads(
                    accepted.cleaned_data['token'],
                    salt=dialogue.SALT,
                    max_age=dialogue.MAX_AGE,
                )
                if payload['patch'] and not accepted.cleaned_data['update_profile']:
                    raise ValueError
                event, patch = dialogue.accept(
                    request.user, pk, accepted.cleaned_data['token']
                )
                if patch:
                    profile = event.request.pair.candidate
                    data = registration.profile_answers(profile)
                    data.update(patch)
                    now = time.time()
                    request.session[KEY] = {
                        'schema': SCHEMA,
                        'created_at': now,
                        'touched_at': now,
                        'token': secrets.token_urlsafe(24),
                        'unlocked': (
                            2
                            if any(name in MobilityForm().fields for name in patch)
                            else 3
                        ),
                        'owner_id': request.user.pk,
                        'editing_user': request.user.pk,
                        'source_profile_updated_at': profile.updated_at.isoformat(),
                        'data': data,
                    }
                    return redirect(
                        '/candidate/prepare/?step='
                        + str(request.session[KEY]['unlocked'])
                        + '&lang='
                        + language
                    )
                return redirect(
                    reverse('candidate_offer_dialogue', args=[pk]) + '?lang=' + language
                )
            elif request.POST.get('action') == 'reply' and form.is_valid():
                proposed = dialogue.make_proposal(
                    request.user,
                    pk,
                    **form.cleaned_data,
                    language=language,
                    prompt=prompt,
                )
                if proposed:
                    token, result = proposed
                    if result.get('clarification'):
                        clarification, turns = result['clarification'], result['turns']
                        form = ReplyForm(
                            initial={
                                **form.cleaned_data,
                                'text': '',
                                'history_token': result['history_token'],
                            }
                        )
                    else:
                        proposal = dict(
                            result,
                            token=token,
                            explanation=dialogue.explanation(result),
                        )
                else:
                    error = _(
                        'Please clarify the scope of your reply. This simulation only recognises the examples below; use the guided form for other replies.'
                    )
            else:
                status = 400
        except (StaleEvaluation, signing.BadSignature):
            error, status = (
                _(
                    'The offer, profile or answers changed. Review the current information before confirming.'
                ),
                409,
            )
        except (ValueError, ValidationError, KeyError, TypeError):
            error, status = (
                _('Review the conditions before recording your answer.'),
                400,
            )
        except ObjectDoesNotExist:
            raise Http404
        except dialogue.dialogue_albert.Unavailable:
            error, status = (
                _(
                    'Albert is unavailable or the reply could not be validated. Your profile has not changed. Use the guided form or try again later.'
                ),
                503,
            )
    if not form.is_bound and current and not clarification:
        latest = obj.answers.filter(question_key=current['key']).order_by('-pk').first()
        form = ReplyForm(
            initial={
                'key': current['key'],
                'fingerprint': current['fingerprint'],
                'context': state['fingerprint'],
                'previous': latest.pk if latest else 0,
            }
        )
    changes = []
    if proposal and proposal['patch']:
        fields = dialogue.dialogue_albert.profile_fields()
        for name, value in proposal['patch'].items():
            field = fields[name]

            def show(v):
                if isinstance(v, bool):
                    return _('Yes') if v else _('No')
                choices = dict(field.choices) if hasattr(field, 'choices') else {}
                if isinstance(v, list):
                    return ', '.join(str(choices.get(item, item)) for item in v) or str(
                        _('Not specified')
                    )
                return (
                    str(choices.get(v, v))
                    if v not in (None, '')
                    else str(_('Not specified'))
                )

            changes.append(
                dict(
                    label=field.label,
                    before=show(getattr(obj.pair.candidate, name)),
                    after=show(value),
                )
            )
    from .shared_views import conversations

    return render(
        request,
        'matching/dialogue.html',
        dict(
            obj=obj,
            shared_conversation=conversations(request.user)
            .filter(confirmation=obj)
            .first(),
            current=current,
            prompt=prompt,
            answered=answered,
            form=form,
            proposal=proposal,
            changes=changes,
            clarification=clarification,
            turns=turns,
            live_dialogue=dialogue.live(),
            error=error,
            before=[
                dict(SCHEDULE_PERIODS)[value]
                for value in obj.pair.candidate.schedule_saturday
            ],
            page_language=language,
            language_question=current['key'] if current else '',
        ),
        status=status,
    )
