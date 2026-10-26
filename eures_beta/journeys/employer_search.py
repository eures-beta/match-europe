"""Explicit local simulation. No external adapter or candidate contact is invoked."""

import os
from django import forms
from django.conf import settings
from django.db import connection, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST, require_http_methods
from .employer_ownership import identity, memberships
from .employer_workspace import connected, visible, render
from .models import EmployerSearchOperation, EmployerSearchEvent


class LaunchForm(forms.Form):
    revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    confirmed = forms.BooleanField(
        label=_(
            'I confirm the start of candidate search, including qualification and contact.'
        )
    )
    scenario = forms.ChoiceField(
        label=_('Local simulation scenario'),
        choices=[
            ('success', _('Confirmed start')),
            ('failure', _('Failure before start')),
            ('timeout_accepted', _('Timeout: request accepted')),
            ('timeout_rejected', _('Timeout: request not accepted')),
        ],
    )


def simulation_enabled():
    return getattr(settings, 'SHARED_DEMO', False) or (
        os.environ.get('ME_LOCAL_REVIEW_ONLY') == '1'
        and os.environ.get('ME_EMPLOYER_SEARCH_SIMULATION') == '1'
    )


def locked_offer(request, id):
    # Same lock namespace as legacy preparation, including its external readback.
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', [str(id)])
    offer = get_object_or_404(visible(request).select_for_update(of=('self',)), pk=id)
    # Lock the explicit membership too: concurrent revocation must not be ignored.
    if (
        not memberships(request)
        .select_for_update()
        .filter(company_id=offer.company_id)
        .first()
    ):
        raise Http404
    return offer


def event(operation, actor):
    EmployerSearchEvent.objects.create(
        operation=operation, actor=actor, state=operation.state
    )


def resolve(operation, offer, actor):
    operation.state = (
        'started' if operation.scenario in ('success', 'timeout_accepted') else 'failed'
    )
    operation.resolved_at = timezone.now()
    operation.save(update_fields=['state', 'resolved_at'])
    if operation.state == 'started':
        offer.search_started_at = operation.resolved_at
    # A failed attempt also changes revision: replay cannot become a new attempt.
    offer.revision += 1
    offer.save(update_fields=['search_started_at', 'revision', 'updated'])
    event(operation, actor)


@connected
@require_http_methods(['GET', 'POST'])
def launch(request, id):
    if not simulation_enabled():
        raise Http404
    with transaction.atomic():
        offer = locked_offer(request, id)
        actor = identity(request)
        form = LaunchForm(
            request.POST if request.method == 'POST' else None,
            initial={'revision': offer.revision},
        )
        if request.method == 'POST' and form.is_valid():
            # Replays of an old confirmation always refer to its original operation.
            existing = offer.search_operations.filter(
                revision=form.cleaned_data['revision']
            ).first()
            if existing:
                return redirect('employer_offer', id=id)
            if (
                offer.search_write_blocked
                or form.cleaned_data['revision'] != offer.revision
            ):
                return render(
                    request, 'search_conflict', offer=offer, status=409, workspace=True
                )
            operation = EmployerSearchOperation.objects.create(
                offer=offer,
                requested_by=actor,
                revision=offer.revision,
                state='pending',
                scenario=form.cleaned_data['scenario'],
            )
            event(operation, actor)
            if operation.scenario.startswith('timeout_'):
                operation.state = 'uncertain'
                operation.save(update_fields=['state'])
                event(operation, actor)
            else:
                resolve(operation, offer, actor)
            return redirect('employer_offer', id=id)
        if offer.search_write_blocked:
            return redirect('employer_offer', id=id)
    return render(request, 'search_confirm', offer=offer, form=form, workspace=True)


@connected
@require_POST
def check(request, id):
    if not simulation_enabled():
        raise Http404
    with transaction.atomic():
        offer = locked_offer(request, id)
        operation = offer.search_operations.filter(
            state__in=['pending', 'uncertain']
        ).first()
        if operation:
            # Simulation of status reconciliation, never a second launch.
            resolve(operation, offer, identity(request))
    return redirect('employer_offer', id=id)
