from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from eures_beta.journeys.access_control import require_identity


@require_POST
@require_identity
def read_notifications(request):
    request.me_user.notifications.filter(read=False).update(read=True)
    return redirect('dashboard')
