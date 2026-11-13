"""Versioned administration policy; account identities never belong in this file."""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q

ACCOUNT_ADMIN_GROUP = 'account-admin'


def get_group_permissions():
    from .models import User
    from eures_beta.invitations.permissions import get_group_permissions as invitations

    return {
        ACCOUNT_ADMIN_GROUP: {User: {'view'}},
        **invitations(),
    }


def synchronize_permissions(database='default'):
    from .models import User

    with transaction.atomic(using=database):
        # Resolve every permission first; a typo or missing migration must not
        # leave a partially applied administration policy.
        definitions = {}
        managed_models = Q(pk__in=[])
        for name, models in get_group_permissions().items():
            permissions = []
            for model, actions in models.items():
                managed_models |= Q(
                    content_type__app_label=model._meta.app_label,
                    content_type__model=model._meta.model_name,
                )
                for action in sorted(actions):
                    try:
                        permission = Permission.objects.using(database).get(
                            content_type__app_label=model._meta.app_label,
                            content_type__model=model._meta.model_name,
                            codename=f'{action}_{model._meta.model_name}',
                        )
                    except Permission.DoesNotExist as error:
                        raise CommandError(
                            'Administration permissions are missing; run migrate first.'
                        ) from error
                    permissions.append(permission)
            definitions[name] = permissions

        eligible = list(
            User.objects.using(database)
            .filter(
                kind=User.Kind.ADVISER,
                is_staff=True,
                is_active=True,
            )
            .values_list('pk', flat=True)
        )
        group_ids = []
        for name, permissions in sorted(definitions.items()):
            group, _ = (
                Group.objects.using(database)
                .select_for_update()
                .get_or_create(name=name)
            )
            group.permissions.set(permissions)
            members = (
                eligible
                if name == ACCOUNT_ADMIN_GROUP
                else list(
                    User.objects.using(database)
                    .filter(kind=User.Kind.ADVISER, is_active=True)
                    .values_list('pk', flat=True)
                )
            )
            group.user_set.set(members)
            group_ids.append(group.pk)

        # User-administration grants have one source of truth. Do not disturb
        # unrelated business permissions or unrelated group memberships.
        admin_permissions = (
            Permission.objects.using(database)
            .filter(managed_models)
            .values_list('pk', flat=True)
        )
        removed_direct, _ = (
            User.user_permissions.through.objects.using(database)
            .filter(
                permission_id__in=admin_permissions,
            )
            .delete()
        )
        removed_unmanaged, _ = (
            Group.permissions.through.objects.using(database)
            .filter(
                permission_id__in=admin_permissions,
            )
            .exclude(group_id__in=group_ids)
            .delete()
        )
        return {
            'groups': len(group_ids),
            'eligible_staff': len(eligible),
            'removed_direct_grants': removed_direct,
            'removed_unmanaged_grants': removed_unmanaged,
        }
