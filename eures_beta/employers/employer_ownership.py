"""Only an active employer account can access its own offers."""

from eures_beta.employers.models import JobOffer


def identity(request):
    user = request.user
    if user.is_authenticated and user.is_active and user.kind == 'employer':
        return user
    return None


def accessible_offers(request):
    person = identity(request)
    return (
        JobOffer.objects.filter(created_by=person)
        if person
        else JobOffer.objects.none()
    )
