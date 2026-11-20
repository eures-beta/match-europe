from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('invitations', '0004_invitation_company')]
    operations = [migrations.RemoveField(model_name='invitation', name='company')]
