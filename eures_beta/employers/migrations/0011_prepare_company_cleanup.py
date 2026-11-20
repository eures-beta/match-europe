"""Order the published branches without rewriting either migration history."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('employers', '0010_remove_joboffer_email_and_more'),
        ('invitations', '0005_remove_invitation_company'),
    ]
    run_before = [('employers', '0009_remove_company_workspaces')]
    operations = []
