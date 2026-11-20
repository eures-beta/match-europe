"""Read-only account overview using the existing workspace access policy."""

from django.core.paginator import Paginator
from django.shortcuts import render

from eures_beta.www.matching.conversations import listed
from eures_beta.www.accounts.views import selected_language

from eures_beta.employers.employer_ownership import accessible_offers


def employer_dashboard(request):
    offers = (
        accessible_offers(request)
        .select_related('created_by')
        .order_by('-updated', '-pk')
    )
    return render(
        request,
        'employer/dashboard.html',
        {
            'shared_conversations': listed(request.user),
            'page_language': selected_language(request),
            'offers': Paginator(offers, 25).get_page(request.GET.get('offers_page')),
            # Shown once, right after an invitation has created the account.
            'welcome': request.session.pop('employer_welcome', False),
        },
    )
