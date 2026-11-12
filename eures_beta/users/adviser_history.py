"""Read-only access to the adviser workspace's recorded data."""

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, Subquery
from django.http import Http404
from django.shortcuts import render

from eures_beta.candidates.registration import profile_answers
from eures_beta.candidates.registration_views import answer_groups
from eures_beta.matching import access
from eures_beta.matching.models import MatchEvaluation, MatchPair

from .models import EmployerInvitation
from .permissions import can_manage_employers
from .views import selected_language


def history(request):
    sections = {}
    if access.can_view_pairs(request.user):
        sections.update(
            candidates='Réponses candidats',
            employers='Réponses employeurs',
        )
        if access.enabled():
            sections['matchings'] = 'Tous les matchings'
    if can_manage_employers(request.user):
        sections['invitations'] = 'Invitations envoyées'
    if not sections:
        raise PermissionDenied

    section = request.GET.get('view') or next(iter(sections))
    if section not in sections:
        raise Http404
    search = request.GET.get('q', '').strip()[:254]
    language = selected_language(request)
    page = Paginator(history_rows(section, search), 20).get_page(request.GET.get('page'))
    selected = request.GET.get('entry')
    selected_entry = None
    if selected and section in ('candidates', 'employers'):
        selected_entry = next((entry for entry in page if str(entry.pk) == selected), None)
    candidate_answers = (
        answer_groups(profile_answers(selected_entry), language)
        if selected_entry and section == 'candidates'
        else []
    )
    return render(
        request,
        'users/adviser_history.html',
        {
            'dashboard_language': language,
            'history_tab': True,
            'sections': sections,
            'section': section,
            'section_title': sections[section],
            'search': search,
            'page': page,
            'selected_entry': selected_entry,
            'candidate_answers': candidate_answers,
        },
    )


def history_rows(section, search):
    if section == 'candidates':
        return access.candidates().filter(
            Q(display_name__icontains=search) | Q(user__email__icontains=search)
        ).order_by('-updated_at', '-pk')
    if section == 'employers':
        return access.offers().filter(
            Q(data__title__icontains=search)
            | Q(data__companyName__icontains=search)
            | Q(email__icontains=search)
        ).order_by('-validated_at', '-pk')
    if section == 'invitations':
        return EmployerInvitation.objects.filter(email_sent_at__isnull=False).filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        ).order_by('-email_sent_at', '-pk')

    latest = MatchEvaluation.objects.filter(pair_id=OuterRef('pk')).order_by('-pk')
    return (
        MatchPair.objects.select_related('candidate__user', 'offer')
        .filter(
            candidate__in=access.candidates(),
            offer__in=access.employer_offers(),
        )
        .filter(
            Q(candidate__display_name__icontains=search)
            | Q(candidate__user__email__icontains=search)
            | Q(offer__data__title__icontains=search)
            | Q(offer__data__companyName__icontains=search)
        )
        .annotate(score=Subquery(latest.values('result__established')[:1]))
        .order_by('-created_at', '-pk')
    )
