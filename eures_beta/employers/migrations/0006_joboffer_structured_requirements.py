from django.db import migrations, models
import eures_beta.employers.offer_requirements


class Migration(migrations.Migration):
    dependencies = [('employers', '0005_employer_profile')]
    operations = [
        migrations.AddField(
            model_name='joboffer',
            name='structured_requirements',
            field=models.JSONField(
                blank=True,
                default=dict,
                validators=[
                    eures_beta.employers.offer_requirements.validate_requirements
                ],
            ),
        ),
    ]
