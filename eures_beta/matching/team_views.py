from functools import wraps
from django import forms
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from eures_beta.users.views import selected_language
from eures_beta.users.permissions import can_manage_employers
from eures_beta.candidates.occupation_choices import resolve_reference
from . import team_access as access, team_services
from .access import local_guard
from .models import MatchEvaluation
from .presentation import present, DECISIONS
from .services import inputs, StaleEvaluation


def entry(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        local_guard(request)
        if not settings.MATCHING_TEAMS_ENABLED:
            raise Http404
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        access.guard(request)
        with translation.override(selected_language(request)):
            return view(request, *args, **kwargs)

    return wrapped


def destination(pair, language):
    return reverse('matching_team_detail', args=[pair.pk]) + '?lang=' + language


class ManualForm(forms.Form):
    candidate = forms.ModelChoiceField(label=_('Candidate'), queryset=None)
    offer = forms.ModelChoiceField(label=_('Job offer'), queryset=None)

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['candidate'].queryset = access.team_candidates(team).order_by(
            'display_name'
        )
        self.fields['candidate'].label_from_instance = lambda item: item.display_name
        self.fields['offer'].queryset = access.team_offers(team).order_by('created')
        self.fields['offer'].label_from_instance = lambda item: item.data.get(
            'title', ''
        )


class OfferFilter(forms.Form):
    offer = forms.ModelChoiceField(label=_('Job offer'), queryset=None, required=False)

    def __init__(self, *args, offers, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['offer'].queryset = offers.order_by('-created')
        self.fields['offer'].label_from_instance = lambda item: item.data.get(
            'title', ''
        )


class DecisionForm(forms.Form):
    evaluation = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    decision_version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    reason = forms.CharField(
        label=_('Professional reason'),
        max_length=2000,
        required=False,
        help_text=_(
            'Required for a manual decision. Explain the professional reason only.'
        ),
        widget=forms.Textarea(attrs={'rows': 3}),
    )


@entry
@require_http_methods(['GET'])
def dashboard(request):
    language = selected_language(request)
    members = list(
        access.memberships(request.user).select_related('team').order_by('team__name')
    )
    query = (
        access.pairs(request.user)
        .select_related('candidate', 'offer', 'team')
        .annotate(
            latest_evaluation_id=Subquery(
                MatchEvaluation.objects.filter(pair_id=OuterRef('pk'))
                .order_by('-id')
                .values('pk')[:1]
            )
        )
        .order_by('-created_at')
    )
    offer_filter = OfferFilter(
        request.GET,
        offers=access.offers().filter(teamoffer__team__in=[m.team_id for m in members]),
    )
    if not offer_filter.is_valid():
        query = query.none()
    elif offer_filter.cleaned_data['offer']:
        query = query.filter(offer=offer_filter.cleaned_data['offer'])
    pairs = list(query)
    evaluations = MatchEvaluation.objects.in_bulk(
        [pair.latest_evaluation_id for pair in pairs if pair.latest_evaluation_id]
    )
    entries = []
    for pair in pairs:
        evaluation = evaluations.get(pair.latest_evaluation_id)
        try:
            data, fingerprint = inputs(pair)
        except ObjectDoesNotExist:
            continue
        previous = pair.decisions.order_by('-id').first()
        entries.append(
            dict(
                pair=pair,
                evaluation=evaluation,
                decision=(
                    _('Refused by an adviser')
                    if pair.decision == 'refused'
                    and previous
                    and previous.decided_by_id
                    else DECISIONS[pair.decision]
                ),
                title=pair.offer.data.get('title', ''),
                stale=bool(evaluation and fingerprint != evaluation.fingerprint),
                manual=bool(
                    pair.source == 'manual'
                    or (evaluation and evaluation.request_mode == 'manual')
                    or (previous and previous.manual)
                ),
                result=present(evaluation.result, language) if evaluation else None,
            )
        )
    entries = [
        entry
        for entry in entries
        if not entry['result']
        or not entry['result']['blocked']
        or entry['manual']
        or entry['pair'].decision != 'pending'
    ]
    entries.sort(
        key=lambda entry: entry['result']['established'] if entry['result'] else -1,
        reverse=True,
    )
    return render(
        request,
        'matching/team_dashboard.html',
        dict(
            adviser_mode=True,
            members=members,
            entries=entries,
            offer_filter=offer_filter,
            can_invite=can_manage_employers(request.user),
            page_language=language,
        ),
    )


@entry
@require_http_methods(['GET', 'POST'])
def manual(request, team_id):
    member = access.require_member(request.user, team_id, decide=True)
    form = ManualForm(
        request.POST if request.method == 'POST' else None, team=member.team
    )
    if request.method == 'POST' and form.is_valid():
        evaluation = team_services.calculate(
            request.user,
            team_id,
            form.cleaned_data['candidate'].pk,
            form.cleaned_data['offer'].pk,
            manual=True,
        )
        return redirect(destination(evaluation.pair, selected_language(request)))
    return render(
        request,
        'matching/team_manual.html',
        dict(form=form, team=member.team, page_language=selected_language(request)),
        status=400 if form.errors else 200,
    )


@entry
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    language = selected_language(request)
    pair = get_object_or_404(
        access.pairs(request.user).select_related('candidate', 'offer', 'team'), pk=pk
    )
    member = access.require_member(request.user, pair.team_id)
    previous = pair.decisions.select_related('decided_by').order_by('-id').first()
    evaluation = pair.evaluations.order_by('-id').first()
    form = DecisionForm(
        (
            request.POST
            if request.method == 'POST' and request.POST.get('action') != 'calculate'
            else None
        ),
        initial={
            'evaluation': evaluation.pk if evaluation else 0,
            'decision_version': previous.pk if previous else 0,
        },
    )
    error, status = '', 200
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'calculate':
                team_services.calculate(
                    request.user, pair.team_id, pair.candidate_id, pair.offer_id
                )
                return redirect(destination(pair, language))
            if action not in ('retained', 'refused', 'manual'):
                raise ValueError()
            if form.is_valid():
                if action == 'manual' and not form.cleaned_data['reason']:
                    form.add_error(
                        'reason',
                        _('A professional reason is required for a manual decision.'),
                    )
                else:
                    team_services.decide(
                        request.user,
                        pair.pk,
                        form.cleaned_data['evaluation'],
                        'retained' if action == 'manual' else action,
                        manual=action == 'manual',
                        reason=form.cleaned_data['reason'],
                        expected_decision=form.cleaned_data['decision_version'],
                    )
                    return redirect(destination(pair, language))
            status = 400
        except StaleEvaluation:
            error, status = (
                _('The answers or evaluation changed. Recalculate before deciding.'),
                409,
            )
        except ObjectDoesNotExist:
            raise Http404
        except ValueError:
            error, status = (
                _('This action is unavailable. Review the blocking points first.'),
                400,
            )
    try:
        data, fingerprint = inputs(pair)
    except ObjectDoesNotExist:
        raise Http404
    stale = bool(evaluation and fingerprint != evaluation.fingerprint)
    result = present(evaluation.result, language) if evaluation else None
    from .models import ConfirmationRequest
    from .confirmation_services import review

    confirmation = ConfirmationRequest.objects.filter(pair=pair).first()
    confirmation_state = review(confirmation) if confirmation else None
    if confirmation_state:
        from .confirmation_views import display_rows

        display_rows(confirmation_state["rows"], language)
    return render(
        request,
        'matching/local.html',
        dict(
            adviser_mode=True,
            confirmation=confirmation,
            confirmation_state=confirmation_state,
            pair=pair,
            occupation_labels=[
                row['label']
                for value in pair.candidate.occupation_references
                if (row := resolve_reference(value, language))
            ],
            evaluation=evaluation,
            result=result,
            decision=(
                _('Refused by an adviser')
                if pair.decision == 'refused' and previous and previous.decided_by_id
                else DECISIONS[pair.decision]
            ),
            stale=stale,
            error=error,
            decision_form=form,
            can_decide=member.can_decide,
            decisions=pair.decisions.select_related('decided_by').order_by(
                '-created_at'
            ),
            decision_outdated=bool(
                previous and evaluation and previous.evaluation_id != evaluation.pk
            ),
            can_retain=bool(
                member.can_decide
                and result
                and not stale
                and not result['blocked']
                and result['matched']
            ),
            can_manual=bool(
                member.can_decide and result and not stale and not result['blocked']
            ),
            page_language=language,
        ),
        status=status,
    )


@entry
@require_http_methods(["GET"])
def employers(request):
    from eures_beta.users.invitation_views import invitation_dashboard

    return invitation_dashboard(request)
