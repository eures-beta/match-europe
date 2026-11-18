"""Three adviser actions, with shared external-search progress."""

from django import forms
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from eures_beta.matching import access, search_queue
from eures_beta.matching.models import AdviserSearchFollowUp, MatchEvaluation
from eures_beta.www.accounts.views import selected_language


class SearchForm(forms.Form):
    searching = forms.BooleanField(
        required=False,
        label=_('Search in progress'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    follow_up_on = forms.DateField(
        required=False,
        label=_('Follow-up date'),
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'
        ),
    )

    def clean(self):
        data = super().clean()
        if data.get('follow_up_on') and not data.get('searching'):
            self.add_error(
                'follow_up_on', _('Start the search before setting a follow-up date.')
            )
        return data


def navigation(counts=None):
    counts = counts or {}
    return [
        {
            'key': 'matchings',
            'title': _('Matchings to validate'),
            'count': counts.get('matchings'),
        },
        {
            'key': 'offers',
            'title': _('Offers without candidates'),
            'count': counts.get('offers'),
        },
        {
            'key': 'candidates',
            'title': _('Candidates without an offer'),
            'count': counts.get('candidates'),
        },
    ]


def action_counts(rows, matching_count):
    today = timezone.localdate()
    counts = {}
    for kind, entries in rows.items():
        counts[kind] = sum(
            not (
                row['followup']
                and row['followup'].searching
                and row['followup'].follow_up_on
                and row['followup'].follow_up_on > today
            )
            for row in entries
        )
    return {**counts, 'matchings': matching_count}


def queue_page(request):
    from . import matching

    allowed = access.can_view_pairs(request.user)
    section = request.GET.get('view', 'matchings')
    if section not in ('matchings', 'offers', 'candidates', 'conversations'):
        raise Http404
    tracking = section == 'conversations'
    rows = search_queue.search_rows() if allowed else {'offers': [], 'candidates': []}
    pending = matching.pending_pairs().order_by('-score', 'pk') if allowed else []
    counts = action_counts(rows, pending.count() if allowed else 0)
    entries = (
        (
            matching.open_conversations().order_by('-created_at', '-pk')
            if allowed
            else []
        )
        if tracking
        else (pending if section == 'matchings' else rows[section])
    )
    page = Paginator(entries, 20).get_page(request.GET.get('page'))
    matchings = []
    if section == 'matchings' and allowed:
        evaluations = MatchEvaluation.objects.in_bulk(
            match.evaluation_id for match in page
        )
        matchings = [
            matching.matching_context(request, match, evaluations[match.evaluation_id])
            for match in page
        ]
    title = next(
        (item['title'] for item in navigation() if item['key'] == section),
        _('Open conversations'),
    )
    return matching.render_workspace(
        request,
        'adviser_matching_queue.html',
        page=page,
        matchings=matchings,
        tracking=tracking,
        allowed=allowed,
        queue_section=section,
        queue_navigation=navigation(counts),
        queue_title=title,
        shared_conversations=(
            matching.listed(request.user) if tracking and allowed else ()
        ),
    )


@never_cache
@require_http_methods(['GET', 'POST'])
def search_detail(request, kind, pk):
    from .matching import pending_pairs, render_workspace
    from .record_details import candidate_details, offer_details

    access.guard(request)
    if kind not in ('offers', 'candidates'):
        raise Http404
    language = selected_language(request)
    with translation.override(language):
        query = access.employer_offers() if kind == 'offers' else access.candidates()
        target = get_object_or_404(query, pk=pk)
        rows = search_queue.search_rows()
        row = next(
            (row for row in rows[kind] if row['object'].pk == pk),
            None,
        )
        if row is None:
            return redirect(
                reverse('dashboard') + '?lang=' + language + '&view=' + kind
            )
        followup = row['followup']
        form = SearchForm(
            request.POST if request.method == 'POST' else None,
            initial={
                'searching': followup.searching if followup else False,
                'follow_up_on': followup.follow_up_on if followup else None,
            },
        )
        if request.method == 'POST' and form.is_valid():
            with transaction.atomic():
                # Serialise creation on the target, including two advisers' first updates.
                get_object_or_404(query.select_for_update(of=('self',)), pk=pk)
                AdviserSearchFollowUp.objects.update_or_create(
                    **(
                        {'offer': target} if kind == 'offers' else {'candidate': target}
                    ),
                    defaults={**form.cleaned_data, 'updated_by': request.user},
                )
            return redirect(
                reverse('adviser_search', args=[kind, pk])
                + '?lang='
                + language
                + '&saved=1'
            )
        details = (
            offer_details(target, language)
            if kind == 'offers'
            else candidate_details(target, language)
        )
        return render_workspace(
            request,
            'adviser_search_detail.html',
            row=row,
            search_form=form,
            **details,
            saved=request.GET.get('saved') == '1',
            queue_section=kind,
            queue_navigation=navigation(action_counts(rows, pending_pairs().count())),
        )
