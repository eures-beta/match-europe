from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class EmployerImport(models.Model):
    """Local sandbox drafts owned by an opaque server-side session, never shared demo identities."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=64, db_index=True)
    email = models.EmailField()
    contact = models.JSONField(default=dict)
    adviser = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='advised_imports')
    preparation_agreed_at = models.DateTimeField()
    source_kind = models.CharField(max_length=10)
    source_url = models.URLField(max_length=2048, blank=True)
    data = models.JSONField(default=dict)
    validated_at = models.DateTimeField(null=True)
    initial_sent_at = models.DateTimeField(null=True)
    synced_at = models.DateTimeField(null=True)
    sandbox_response = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Profile(models.Model):
    class Role(models.TextChoices):
        EMPLOYER = 'employer', _('Employer')
        CANDIDATE = 'candidate', _('Candidate')
        ADVISER = 'adviser', _('Adviser')
        ADMIN = 'admin', _('Administrator')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=16, choices=Role.choices)
    verified = models.BooleanField(default=False)
    adviser = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='supported_profiles')
    name = models.CharField(max_length=150, blank=True)


class AccessToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)


class Document(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='pdf/%Y/%m/')
    text = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)


class Offer(models.Model):
    class State(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PENDING = 'pending', _('Awaiting email confirmation')
        READY = 'ready', _('Validated')
        SYNCED = 'synced', _('Sent to matching — demonstration')
    employer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='offers')
    adviser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='advised_offers')
    document = models.OneToOneField(Document, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=125)
    company = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    description = models.TextField(max_length=16000)
    contract = models.CharField(max_length=150, blank=True)
    salary = models.CharField(max_length=150, blank=True)
    hours = models.CharField(max_length=150, blank=True)
    languages = models.CharField(max_length=250, blank=True)
    skills = models.CharField(max_length=500, blank=True)
    cross_border = models.CharField(max_length=12, blank=True)
    relocation = models.CharField(max_length=12, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.DRAFT)
    validated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)


class Question(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    expectation = models.CharField(max_length=500, blank=True)
    options = models.CharField(max_length=500, blank=True)
    mandatory = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['position', 'pk']
    def choices(self):
        return [x.strip() for x in self.options.split('|') if x.strip()]


class Candidate(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidate')
    document = models.OneToOneField(Document, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=150)
    experience = models.TextField(max_length=12000)
    jobs = models.CharField(max_length=500)
    skills = models.CharField(max_length=500, blank=True)
    languages = models.CharField(max_length=250, blank=True)
    location = models.CharField(max_length=150)
    availability = models.CharField(max_length=150)
    cross_border = models.CharField(max_length=12)
    relocation = models.CharField(max_length=12)
    validated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)


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
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='matches')
    state = models.CharField(max_length=16, choices=State.choices, default=State.SUGGESTED)
    explanation = models.TextField()
    candidate_agreement = models.BooleanField(default=False)
    employer_agreement = models.BooleanField(default=False)
    review_note = models.TextField(blank=True, max_length=2000)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['offer', 'candidate'], name='unique_candidate_offer')]


class Answer(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    choice = models.CharField(max_length=500, blank=True)
    text = models.TextField(max_length=4000, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['match', 'question'], name='unique_answer')]


class Conversation(models.Model):
    match = models.OneToOneField(Match, on_delete=models.PROTECT, related_name='conversation')
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=4000)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created', 'pk']


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    label = models.CharField(max_length=200)
    url = models.CharField(max_length=200)
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)


class Event(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=40)
    object_id = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)


class EmployerEmailLink(models.Model):
    """Local-only email verification; no business permissions are granted."""
    email = models.EmailField()
    digest = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)
