from eures_beta.offers.models import Offer, Question
from eures_beta.candidates.models import Candidate
from django.db import models
from django.utils.translation import gettext_lazy as _


class Match(models.Model):
    class State(models.TextChoices):
        SUGGESTED = 'suggested', _('Suggested — adviser review')
        INVITED = 'invited', _('Offer proposed')
        DECLINED = 'declined', _('Not interested')
        ANSWERING = 'answering', _('Prequalification in progress')
        REVIEW = 'review', _('Awaiting adviser review')
        INTRODUCED = 'introduced', _('Conversation opened')
        CLARIFY = 'clarify', _('Clarification needed')

    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='matches')
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name='matches'
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.SUGGESTED
    )
    explanation = models.TextField()
    candidate_agreement = models.BooleanField(default=False)
    employer_agreement = models.BooleanField(default=False)
    review_note = models.TextField(blank=True, max_length=2000)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journeys_match'
        constraints = [
            models.UniqueConstraint(
                fields=['offer', 'candidate'], name='unique_candidate_offer'
            )
        ]


class Answer(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    choice = models.CharField(max_length=500, blank=True)
    text = models.TextField(max_length=4000, blank=True)

    class Meta:
        db_table = 'journeys_answer'
        constraints = [
            models.UniqueConstraint(fields=['match', 'question'], name='unique_answer')
        ]
