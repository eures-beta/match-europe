"""Read-only account overview using the existing workspace access policy."""

from django.core.paginator import Paginator
from django.shortcuts import render

from eures_beta.matching.shared_views import listed
from eures_beta.users.views import selected_language

from .employer_ownership import accessible_imports


def employer_dashboard(request):
    from eures_beta.skills.continuous import trial_request

    # Never include browser-only anonymous drafts in an authenticated account list.
    offers = (
        accessible_imports(request)
        .exclude(company__isnull=True, created_by__isnull=True)
        .select_related('company')
        .order_by('-updated', '-pk')
    )
    return render(
        request,
        'employer/dashboard.html',
        {
            'shared_conversations': listed(request.user),
            'page_language': selected_language(request),
            'continuous_skills': trial_request(request),
            'offers': Paginator(offers, 25).get_page(request.GET.get('offers_page')),
            # Shown once, right after an invitation has created the account.
            'welcome': request.session.pop('employer_welcome', False),
        },
    )
