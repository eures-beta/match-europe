"""Deposit and telephone confirmation without manufacturing employer accounts."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import Company, CompanyMembership
from .offer_validation import clean_data


def guard(user):
    if not user.is_authenticated or not user.is_active or user.kind != 'adviser':
        raise PermissionDenied


def confirm(offer, adviser, date):
    guard(adviser)
    if not date or date > timezone.localdate():
        raise ValidationError(
            _('Enter the date of the telephone confirmation, no later than today.')
        )
    if not all(
        offer.data.get(key)
        for key in ('title', 'companyName', 'city', 'description', 'contractType')
    ):
        raise ValidationError(
            _(
                'Complete job title, company, location, description and contract type before confirming.'
            )
        )
    offer.phone_confirmed_on = date
    offer.phone_recorded_at = timezone.now()
    offer.phone_recorded_by = adviser
    offer.phone_confirmed_revision = offer.revision
    offer.validated_at = timezone.now()


@transaction.atomic
def create(offer, adviser, setup):
    """Setup is a server-owned session value, never an authorization from the payload."""
    guard(adviser)
    from eures_beta.users.models import User

    User.objects.select_for_update().get(pk=adviser.pk)
    existing = (
        type(offer).objects.filter(pk=setup['offer_id'], created_by=adviser).first()
    )
    if existing:
        return existing
    offer.pk = setup['offer_id']

    company = (
        Company.objects.select_for_update().get(pk=setup['company'])
        if setup['company']
        else Company.objects.create(name=setup['company_name'])
    )
    if setup.get('employer'):
        employer = (
            User.objects.select_for_update()
            .filter(pk=setup['employer'], kind='employer', is_active=True)
            .first()
        )
        if not employer:
            raise PermissionDenied
        # Existing workspaces require existing membership. A new workspace is an
        # explicit grant made by the adviser, not an email-based inference.
        if setup['company']:
            if not CompanyMembership.objects.filter(
                company=company, user=employer, active=True
            ).exists():
                raise PermissionDenied
        else:
            CompanyMembership.objects.create(company=company, user=employer)
    offer.company = company
    offer.created_by = adviser
    offer.adviser = adviser
    offer.employer_contact_id = setup.get('employer')
    offer.email = offer.contact['email']
    offer.data = clean_data({**offer.data, 'companyName': company.name})
    offer.save()
    return offer
