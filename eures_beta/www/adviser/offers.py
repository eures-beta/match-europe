"""Adviser deposits reuse the employer import and editing validations."""

import time
import uuid
from functools import wraps

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.debug import sensitive_post_parameters

from eures_beta.employers.adviser_deposit import guard, confirm
from eures_beta.employers.models import JobOffer
from eures_beta.matching.services import schedule_offer_matching
from eures_beta.www.accounts.views import selected_language
from eures_beta.www.employer.forms import EmployerContactForm
from eures_beta.www.employer.imports import import_response, read_source_response
from eures_beta.www.employer.pages import render_page
from eures_beta.www.employer.workspace import OfferEditForm
from .offer_forms import DepositSetupForm, PhoneConfirmationForm


def adviser_required(view):
    @sensitive_post_parameters()
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        guard(request.user)
        request.session['login_language'] = selected_language(request)
        with translation.override(selected_language(request)):
            return view(request, *args, **kwargs)

    return wrapped


def setup_for(request):
    setup = request.session.get('adviser_offer_setup', {})
    if setup.get('actor') != request.user.pk or time.time() - setup.get('at', 0) > 3600:
        return None
    return setup


@never_cache
@adviser_required
@require_http_methods(['GET', 'POST'])
def portfolio(request):
    form = DepositSetupForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        values = form.cleaned_data
        request.session['adviser_offer_setup'] = {
            'actor': request.user.pk,
            'at': time.time(),
            'offer_id': str(uuid.uuid4()),
            'email': values['email'],
        }
        return redirect('adviser_offer_import')
    return render(
        request,
        'users/adviser_offers.html',
        {
            'form': form,
            'dashboard_language': selected_language(request),
            'deposit_tab': True,
            'offers': Paginator(
                JobOffer.objects.filter(adviser=request.user)
                .select_related('employer')
                .order_by('-updated', 'pk'),
                25,
            ).get_page(request.GET.get('page')),
        },
    )


@never_cache
@ensure_csrf_cookie
@adviser_required
@require_http_methods(['GET'])
def import_offer(request):
    setup = setup_for(request)
    if not setup:
        return redirect('adviser_offers')
    return render_page(
        request, 'import.html', adviser_setup=setup, phone_form=PhoneConfirmationForm()
    )


@never_cache
@adviser_required
@require_POST
def source(request):
    setup = setup_for(request)
    if not setup or request.headers.get('X-Deposit-Token') != setup['offer_id']:
        return JsonResponse({'error': 'deposit_expired'}, status=409)
    response = read_source_response(request)
    if response.status_code == 200:
        pending = request.session['pending_offer_source']
        request.session['pending_offer_source'] = {
            **pending,
            'deposit_id': setup['offer_id'],
        }
    return response


@never_cache
@adviser_required
@require_http_methods(['GET', 'POST'])
def deposits(request):
    setup = setup_for(request)
    if not setup or request.headers.get('X-Deposit-Token') != setup['offer_id']:
        return JsonResponse({'error': 'deposit_expired'}, status=409)
    if request.method == 'GET':
        return JsonResponse({'drafts': []})
    if (
        request.POST.get('sourceToken')
        and request.session.get('pending_offer_source', {}).get('deposit_id')
        != setup['offer_id']
    ):
        return JsonResponse({'error': 'deposit_expired'}, status=409)
    return import_response(request, adviser_setup=setup)


@never_cache
@adviser_required
@require_http_methods(['GET', 'POST'])
def detail(request, id):
    with transaction.atomic():
        offer = get_object_or_404(
            JobOffer.objects.select_for_update(),
            pk=id,
            adviser=request.user,
            employer__kind='employer',
        )
        form = OfferEditForm(
            request.POST if request.method == 'POST' else None, offer=offer
        )
        contact = EmployerContactForm(
            request.POST if request.method == 'POST' else None,
            initial={'email': offer.employer.email, **offer.contact},
            prefix='contact',
        )
        contact.fields['email'].disabled = True
        phone = PhoneConfirmationForm(
            request.POST if request.method == 'POST' else None
        )
        if (
            request.method == 'POST'
            and form.is_valid() & contact.is_valid() & phone.is_valid()
        ):
            if (
                form.cleaned_data['revision'] != offer.revision
                or offer.search_write_blocked
            ):
                from django.utils.translation import gettext as _

                form.add_error(
                    None,
                    _(
                        'This offer changed or its search has already started. Reload the page.'
                    ),
                )
            else:
                offer.data = form.offer_data
                offer.contact = contact.cleaned_data
                offer.revision += 1
                try:
                    confirm(offer, request.user, phone.cleaned_data['confirmed_on'])
                except ValidationError as exc:
                    phone.add_error(None, exc)
                else:
                    offer.save()
                    schedule_offer_matching(offer)
                    return redirect('adviser_offer', id=offer.pk)
    return render(
        request,
        'users/adviser_offer.html',
        {
            'offer': offer,
            'form': form,
            'contact': contact,
            'phone_form': phone,
            'dashboard_language': selected_language(request),
            'deposit_tab': True,
            'contract_label': dict(form.fields['contractType'].choices).get(
                offer.data.get('contractType'), ''
            ),
        },
    )
