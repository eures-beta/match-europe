from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import OuterRef, Subquery
from django.http import Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .access import guard, candidates, offers, can_change_pair
from .confirmation_services import review
from .confirmation_views import display_rows
from .models import MatchPair, MatchEvaluation, ConfirmationRequest
from .services import calculate, decide, inputs, StaleEvaluation
from .presentation import present, DECISIONS
from eures_beta.candidates.occupation_choices import resolve_reference


class PairForm(forms.Form):
    candidate = forms.ModelChoiceField(label=_('Fictional candidate'), queryset=None)
    offer = forms.ModelChoiceField(label=_('Fictional offer'), queryset=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['candidate'].queryset = candidates().order_by('display_name', 'pk')
        self.fields['candidate'].label_from_instance = lambda obj: obj.display_name
        self.fields['offer'].queryset = offers().order_by('created', 'pk')
        self.fields['offer'].label_from_instance = lambda obj: obj.data.get(
            'title'
        ) or str(_('Untitled offer'))


def lang(request):
    value = request.GET.get('lang', 'fr')
    return value if value in ('fr', 'en', 'de') else 'fr'


def destination(pair, language):
    return reverse('matching_detail', args=[pair.pk]) + '?lang=' + language


@never_cache
@require_http_methods(['GET', 'POST'])
def index(request):
    guard(request)
    language = lang(request)
    with translation.override(language):
        form = PairForm(request.POST if request.method == 'POST' else None)
        if request.method == 'POST' and form.is_valid():
            evaluation = calculate(**form.cleaned_data)
            return redirect(destination(evaluation.pair, language))
        pairs = (
            MatchPair.objects.filter(candidate__in=candidates(), offer__in=offers())
            .select_related('candidate', 'offer')
            .annotate(
                latest_evaluation_id=Subquery(
                    MatchEvaluation.objects.filter(pair_id=OuterRef('pk'))
                    .order_by('-id')
                    .values('pk')[:1]
                )
            )
            .order_by('-created_at')
        )
        pairs = list(pairs)
        evaluations = MatchEvaluation.objects.in_bulk(
            [p.latest_evaluation_id for p in pairs if p.latest_evaluation_id]
        )
        entries = []
        for pair in pairs:
            evaluation = evaluations.get(pair.latest_evaluation_id)
            stale = False
            if evaluation:
                try:
                    data, fingerprint = inputs(pair)
                    stale = fingerprint != evaluation.fingerprint
                except ObjectDoesNotExist:
                    continue
            entries.append(
                dict(
                    pair=pair,
                    decision=DECISIONS[pair.decision],
                    title=pair.offer.data.get('title', ''),
                    evaluation=evaluation,
                    result=present(evaluation.result, language) if evaluation else None,
                    stale=stale,
                )
            )
        return render(
            request,
            'matching/results.html',
            dict(form=form, entries=entries, page_language=language),
            status=400 if form.errors else 200,
        )


@never_cache
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    guard(request)
    pair = get_object_or_404(
        MatchPair.objects.filter(
            candidate__in=candidates(), offer__in=offers()
        ).select_related('candidate', 'offer'),
        pk=pk,
    )
    language = lang(request)
    error, status = '', 200
    with translation.override(language):
        if request.method == 'POST':
            try:
                if request.POST.get('action') == 'calculate':
                    calculate(pair.candidate, pair.offer)
                elif request.POST.get('action') in ('retained', 'refused'):
                    decide(
                        pair.pk,
                        int(request.POST.get('evaluation', '')),
                        request.POST['action'],
                    )
                else:
                    raise ValueError()
                return redirect(destination(pair, language))
            except StaleEvaluation:
                error, status = (
                    _(
                        'The answers or evaluation changed. Recalculate before deciding.'
                    ),
                    409,
                )
            except ObjectDoesNotExist:
                raise Http404
            except ValueError:
                error, status = (
                    _('This action is unavailable. Review the blocking points first.'),
                    400,
                )
        confirmation = ConfirmationRequest.objects.filter(pair=pair).first()
        confirmation_state = review(confirmation) if confirmation else None
        if confirmation_state:
            display_rows(confirmation_state['rows'], language)
        evaluation = pair.evaluations.order_by('-id').first()
        try:
            input_data, current = inputs(pair)
        except ObjectDoesNotExist:
            raise Http404
        stale = bool(evaluation and evaluation.fingerprint != current)
        result = present(evaluation.result, language) if evaluation else None
        return render(
            request,
            'matching/results.html',
            dict(
                pair=pair,
                can_request_confirmation=can_change_pair(request.user),
                confirmation=confirmation,
                confirmation_state=confirmation_state,
                occupation_labels=[
                    row['label']
                    for value in pair.candidate.occupation_references
                    if (row := resolve_reference(value, language))
                ],
                evaluation=evaluation,
                result=result,
                decision=DECISIONS[pair.decision],
                stale=stale,
                error=error,
                page_language=language,
                decisions=pair.decisions.order_by('-created_at'),
                can_retain=bool(
                    result and not stale and not result['blocked'] and result['matched']
                ),
            ),
            status=status,
        )
