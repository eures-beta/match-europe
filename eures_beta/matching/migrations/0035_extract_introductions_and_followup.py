"""Transfer model ownership without dropping any table or changing grants."""

from django.db import migrations
from ._domain_transfer import forward_content_types, backward_content_types


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0034_merge_employer_review_and_followup'),
        ('introductions', '0001_initial'),
        ('followup', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='EmployerCandidateReview'),
                migrations.DeleteModel(name='CandidateOfferConversationMessage'),
                migrations.DeleteModel(name='CandidateOfferConversation'),
                migrations.DeleteModel(name='CandidateProfileSharing'),
                migrations.DeleteModel(name='CandidateOfferReviewAnswer'),
                migrations.DeleteModel(name='CandidateOfferReviewEvent'),
                migrations.DeleteModel(name='CandidateOfferReview'),
                migrations.DeleteModel(name='MatchConclusionEvent'),
                migrations.DeleteModel(name='MatchConclusion'),
                migrations.DeleteModel(name='MatchFollowupEvent'),
                migrations.DeleteModel(name='MatchFollowup'),
                migrations.DeleteModel(name='CandidateSupport'),
                migrations.DeleteModel(name='JobOfferSupport'),
            ]
        ),
        migrations.RunPython(forward_content_types, backward_content_types),
    ]
