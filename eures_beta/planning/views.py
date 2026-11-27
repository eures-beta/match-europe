"""Weekly availability for active staff, irrespective of business role."""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from django.contrib.auth import get_user_model
from .models import StaffDailyAvailability

WEEK = timedelta(days=7)
LAST_WEEK = date.max - timedelta(days=6)


def parse_day(value):
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None
    return day if day.isoformat() == value else None


def monday(day):
    return day - timedelta(days=day.weekday())


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def planning(request):
    if not (
        request.user.is_authenticated
        and request.user.is_active
        and request.user.is_staff
    ):
        raise Http404
    language = request.LANGUAGE_CODE
    today = timezone.localdate()
    selected = parse_day(request.GET.get('week', today.isoformat()))
    if selected is None or monday(selected) > LAST_WEEK:
        return HttpResponseBadRequest(_('Invalid planning week.'))

    start = monday(selected)
    days = [start + timedelta(days=index) for index in range(7)]
    if request.method == 'POST':
        day = parse_day(request.POST.get('day', ''))
        status = request.POST.get('status')
        if day not in days or status not in ('present', 'absent'):
            return HttpResponseBadRequest(_('Invalid availability.'))
        StaffDailyAvailability.objects.update_or_create(
            user=request.user, day=day, defaults={'present': status == 'present'}
        )
        return redirect(
            reverse('staff_planning', query={'lang': language, 'week': start})
        )

    users = (
        get_user_model()
        .objects.filter(is_active=True, is_staff=True)
        .order_by('last_name', 'first_name', 'pk')
    )
    availability = {
        (user_id, day): present
        for user_id, day, present in StaffDailyAvailability.objects.filter(
            user__in=users, day__range=(start, days[-1])
        ).values_list('user_id', 'day', 'present')
    }
    statuses = {
        True: ('present', _('Present'), 'absent', _('Mark as absent')),
        False: ('absent', _('Absent'), 'present', _('Mark as present')),
    }
    rows = [
        {
            'name': user.get_full_name() or _('Staff %(number)s') % {'number': user.pk},
            'organisation': user.organization_name,
            'own': user.pk == request.user.pk,
            'days': [
                (day, *statuses[availability.get((user.pk, day), day.weekday() < 5)])
                for day in days
            ],
        }
        for user in users
    ]
    return render(
        request,
        'planning/week.html',
        {
            'dashboard_language': language,
            'planning_tab': True,
            'days': days,
            'start': start,
            'end': days[-1],
            'previous_week': start - WEEK if start > date.min else None,
            'next_week': start + WEEK if start <= LAST_WEEK - WEEK else None,
            'rows': rows,
        },
    )
