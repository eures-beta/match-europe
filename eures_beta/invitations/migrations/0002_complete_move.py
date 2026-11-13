"""An app-targeted migrate must complete the transfer before post_migrate."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('invitations', '0001_initial'),
        ('users', '0009_move_invitation_to_own_app'),
    ]
    operations = []
