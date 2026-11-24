"""Read-only access to the adviser workspace's recorded data."""

import uuid

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.http import Http404
from django.shortcuts import render
from django.utils.translation import gettext as _

from eures_beta.candidates.registration import profile_answers
from eures_beta.www.candidate.registration import answer_groups
from eures_beta.matching import access
from eures_beta.matching.models import CandidateOfferMatch, MatchEvaluation

from eures_beta.invitations.models import Invitation
from eures_beta.employers.models import JobOffer
from eures_beta.www.adviser.offer_details import offer_details
from eures_beta.invitations.permissions import can_invite
from eures_beta.www.accounts.views import selected_language


def history(request):
    sections = {}
    if access.can_view_pairs(request.user):
        sections.update(
            candidates='Réponses candidats',
            employers=_('Employer job offers'),
        )
        sections['matchings'] = 'Tous les matchings'
    if can_invite(request.user):
        sections['invitations'] = 'Invitations envoyées'
    if not sections:
        raise PermissionDenied

    section = request.GET.get('view') or next(iter(sections))
    if section not in sections:
        raise Http404
    search = request.GET.get('q', '').strip()[:254]
    language = selected_language(request)
    selected = request.GET.get('entry')
    employer = None
    if section == 'employers':
        employer = selected_employer(request.GET.get('employer'), selected)
    if section == 'employers' and employer is None:
        page = Paginator(employer_groups(search), 20).get_page(request.GET.get('page'))
        describe_employer_groups(page)
    else:
        rows = history_rows(section, search)
        if employer is not None:
            rows = rows.filter(**employer_filter(employer['key']))
        page = Paginator(rows, 20).get_page(request.GET.get('page'))
    selected_entry = None
    if selected and (section == 'candidates' or employer is not None):
        selected_entry = next(
            (entry for entry in page if str(entry.pk) == selected), None
        )
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
            'employer': employer,
            'selected_entry': selected_entry,
            'candidate_answers': candidate_answers,
            'offer_details': (
                offer_details(selected_entry, language)
                if selected_entry and section == 'employers'
                else []
            ),
        },
    )


def offer_search(rows, search):
    if not search:
        return rows
    return rows.filter(
        Q(data__title__icontains=search)
        | Q(data__companyName__icontains=search)
        | Q(employer__email__icontains=search)
        | Q(data__city__icontains=search)
    )


def employer_filter(key):
    # Offers recorded before employer accounts existed are grouped under 'none'.
    return {'employer__isnull': True} if key == 'none' else {'employer_id': key}


def selected_employer(key, entry):
    """The employer whose offers are listed, from `employer` or from an offer link."""
    if not key and entry:
        if not is_uuid(entry):
            return None
        offer = JobOffer.objects.filter(pk=entry).values('employer_id').first()
        if offer is None:
            return None
        key = str(offer['employer_id'] or 'none')
    if key != 'none' and not (key or '').isdigit():
        return None
    offers = JobOffer.objects.filter(**employer_filter(key))
    latest = offers.order_by('-updated', '-pk').select_related('employer').first()
    if latest is None:
        return None
    return {
        'key': key,
        'company': latest.data.get('companyName', ''),
        'email': latest.employer.email if latest.employer else '',
        'offer_count': offers.count(),
    }


def is_uuid(value):
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def employer_groups(search):
    """One row per employer account, counting its offers that match the search."""
    return (
        offer_search(JobOffer.objects.all(), search)
        .values('employer')
        .annotate(offer_count=Count('pk'), last_update=Max('updated'))
        .order_by('-last_update', 'employer')
    )


def describe_employer_groups(page):
    """Add the company name of each employer's latest offer and the account email."""
    keys = [row['employer'] for row in page.object_list]
    page.object_list = list(page.object_list)
    accounts = Q(employer__in=[key for key in keys if key])
    if None in keys:
        accounts |= Q(employer__isnull=True)
    rows = (
        JobOffer.objects.filter(accounts)
        .order_by('-updated', '-pk')
        .values('employer', 'employer__email', 'data__companyName')
    )
    latest = {}
    for row in rows:
        latest.setdefault(row['employer'], row)
    for group in page.object_list:
        row = latest.get(group['employer'], {})
        group['key'] = str(group['employer'] or 'none')
        group['company'] = row.get('data__companyName') or ''
        group['email'] = row.get('employer__email') or ''


def history_rows(section, search):
    if section == 'candidates':
        return (
            access.candidates()
            .filter(
                Q(display_name__icontains=search) | Q(user__email__icontains=search)
            )
            .order_by('-updated_at', '-pk')
        )
    if section == 'employers':
        # Adviser history mirrors recorded offers, independently of matching eligibility.
        rows = offer_search(
            JobOffer.objects.select_related('employer', 'adviser'), search
        )
        return rows.order_by('-created', '-pk')
    if section == 'invitations':
        return (
            Invitation.objects.filter(email_sent_at__isnull=False)
            .filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
            .order_by('-email_sent_at', '-pk')
        )

    latest = MatchEvaluation.objects.filter(match_id=OuterRef('pk')).order_by('-pk')
    return (
        CandidateOfferMatch.objects.select_related('candidate__user', 'offer')
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
