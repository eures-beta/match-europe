"""Weekly availability for active EURES advisers."""

from datetime import date, timedelta

from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from eures_beta.users.models import AdviserAvailability, User
from eures_beta.www.accounts.views import selected_language
from .offers import adviser_required

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
@adviser_required
@require_http_methods(['GET', 'POST'])
def planning(request):
    language = selected_language(request)
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
        AdviserAvailability.objects.update_or_create(
            adviser=request.user, day=day, defaults={'present': status == 'present'}
        )
        return redirect(
            reverse('adviser_planning', query={'lang': language, 'week': start})
        )

    advisers = User.objects.filter(is_active=True, kind=User.Kind.ADVISER).order_by(
        'last_name', 'first_name', 'pk'
    )
    availability = {
        (adviser_id, day): present
        for adviser_id, day, present in AdviserAvailability.objects.filter(
            adviser__in=advisers, day__range=(start, days[-1])
        ).values_list('adviser_id', 'day', 'present')
    }
    statuses = {
        True: ('present', _('Present'), 'absent', _('Mark as absent')),
        False: ('absent', _('Absent'), 'present', _('Mark as present')),
    }
    rows = [
        {
            'name': adviser.get_full_name()
            or _('Adviser %(number)s') % {'number': adviser.pk},
            'organisation': adviser.organization_name,
            'own': adviser.pk == request.user.pk,
            'days': [
                (day, *statuses[availability.get((adviser.pk, day), True)])
                for day in days
            ],
        }
        for adviser in advisers
    ]
    return render(
        request,
        'users/adviser_planning.html',
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
