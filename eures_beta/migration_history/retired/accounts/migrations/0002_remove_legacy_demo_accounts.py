"""Remove only the four reserved identities and their obsolete scenario data."""

from django.db import migrations


def remove_legacy_demo(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model('auth', 'User')
    usernames = [
        f'{role}@example.invalid'
        for role in ('adviser', 'employer', 'candidate', 'admin')
    ]
    users = User.objects.using(alias).filter(username__in=usernames)
    # A reserved name reused for a real/operator account requires human inspection.
    if any(
        user.is_staff or user.is_superuser or not user.password.startswith('!')
        for user in users
    ):
        raise RuntimeError(
            'Reserved demo identity has credentials or operator privileges; inspect before deleting.'
        )
    ids = list(users.values_list('pk', flat=True))
    if not ids:
        return
    Offer = apps.get_model('offers', 'Offer')
    Candidate = apps.get_model('candidates', 'Candidate')
    Match = apps.get_model('matching', 'Match')
    Conversation = apps.get_model('conversations', 'Conversation')
    from django.db.models import Q

    # Never cascade into a scenario owned by another account.
    if (
        Offer.objects.using(alias)
        .filter(adviser_id__in=ids)
        .exclude(employer_id__in=ids)
        .exists()
    ):
        raise RuntimeError(
            'Demo adviser is attached to another account’s offer; inspect before deleting.'
        )
    offers = Offer.objects.using(alias).filter(employer_id__in=ids)
    candidates = Candidate.objects.using(alias).filter(user_id__in=ids)
    matches = Match.objects.using(alias).filter(
        Q(offer_id__in=offers.values('pk'))
        | Q(candidate_id__in=candidates.values('pk'))
    )
    conversations = Conversation.objects.using(alias).filter(
        match_id__in=matches.values('pk')
    )
    apps.get_model('conversations', 'Message').objects.using(alias).filter(
        conversation_id__in=conversations.values('pk')
    ).delete()
    conversations.delete()
    apps.get_model('matching', 'Answer').objects.using(alias).filter(
        match_id__in=matches.values('pk')
    ).delete()
    matches.delete()
    apps.get_model('offers', 'Question').objects.using(alias).filter(
        offer_id__in=offers.values('pk')
    ).delete()
    offers.delete()
    candidates.delete()
    # Keep current employer imports and their content; only detach the retired adviser.
    apps.get_model('employers', 'EmployerImport').objects.using(alias).filter(
        adviser_id__in=ids
    ).update(adviser_id=None)
    apps.get_model('accounts', 'Profile').objects.using(alias).filter(
        adviser_id__in=ids
    ).update(adviser_id=None)
    apps.get_model('accounts', 'Profile').objects.using(alias).filter(
        user_id__in=ids
    ).delete()
    apps.get_model('accounts', 'AccessToken').objects.using(alias).filter(
        user_id__in=ids
    ).delete()
    apps.get_model('accounts', 'Event').objects.using(alias).filter(
        actor_id__in=ids
    ).delete()
    apps.get_model('notifications', 'Notification').objects.using(alias).filter(
        user_id__in=ids
    ).delete()
    apps.get_model('documents', 'Document').objects.using(alias).filter(
        owner_id__in=ids
    ).delete()
    users.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('journeys', '0018_delete_match'),
        ('employers', '0001_initial'),
    ]
    # The obsolete fictional data is intentionally not recreated on rollback.
    operations = [migrations.RunPython(remove_legacy_demo, migrations.RunPython.noop)]
