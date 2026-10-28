from eures_beta.accounts.services import audit
from django.utils.translation import gettext_noop

from django.utils import timezone
from django.utils.translation import gettext as _

from eures_beta.notifications.models import Notification
from eures_beta.offers.models import Offer


def dispatch_offer(offer, actor):
    """Offline adapter: does not call AGLAE or start a qualification."""
    if not offer.validated_at or not offer.employer.profile.verified:
        raise ValueError(_('Validate the offer and confirm your email first.'))
    if offer.sent_at:
        return
    offer.sent_at = timezone.now()
    offer.state = Offer.State.SYNCED
    offer.save(update_fields=['state', 'sent_at'])
    audit(actor, 'demo_offer_dispatched', offer)
    Notification.objects.create(
        user=offer.adviser,
        label=gettext_noop('New validated offer'),
        url=f'/offers/{offer.pk}/',
    )
