from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .permissions import EMPLOYER_INVITER_GROUP


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_invitation_group(sender, instance, created, raw, using, **kwargs):
    if created and not raw and instance.kind == 'adviser' and instance.is_active:
        instance.groups.add(
            *Group.objects.using(using).filter(name=EMPLOYER_INVITER_GROUP)
        )
