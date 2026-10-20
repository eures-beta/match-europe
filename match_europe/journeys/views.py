from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from .forms import ImportAssignmentForm, AccessForm, CandidateForm, MessageForm, OfferForm, QuestionForm, ReviewForm, UploadForm
from .models import Answer, Candidate, Conversation, Document, Event, Match, Message, Notification, Offer, Profile, Question
from .services import adviser_from, audit, consume_token, dispatch_offer, extract_pdf, invite_for, issue_token, notify, suggest_candidates

def interface(request):
    user = identity(request)
    return {'me_user': user, 'demo_mode': settings.DEMO_MODE, 'notifications': user.notifications.order_by('-created')[:8] if user else []}

def identity(request):
    if request.user.is_authenticated:
        return request.user
    draft_id = request.session.get('draft_user')
    if draft_id:
        return User.objects.filter(pk=draft_id, profile__verified=False, profile__role__in=['candidate', 'employer']).first()
    return None

def require_identity(view):

    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        user = identity(request)
        if not user:
            return redirect('access')
        request.me_user = user
        return view(request, *args, **kwargs)
    return wrapped

def forbid():
    raise Http404()

def allowed_offer(user, offer):
    return user.pk == offer.employer_id or (user.profile.verified and (user.pk == offer.adviser_id or user.profile.role == 'admin'))

def allowed_match(user, match):
    if not user.profile.verified:
        return False
    if user.profile.role == 'admin' or user.pk in [match.candidate.user_id, match.offer.adviser_id]:
        return True
    return user.pk == match.offer.employer_id and match.state in [Match.State.REVIEW, Match.State.CLARIFY, Match.State.INTRODUCED]

@never_cache
def access(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    invitation = request.GET.get('invite', '') or request.session.get('invitation', '')
    adviser = adviser_from(invitation)
    if adviser:
        request.session['invitation'] = invitation
    role = request.GET.get('role', '') or request.session.get('start_role', '')
    if role in ['employer', 'candidate']:
        request.session['start_role'] = role
    form = AccessForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        user = User.objects.filter(username=email).first()
        if not user and adviser and (role in ['employer', 'candidate']):
            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email)
                user.set_unusable_password()
                user.save()
                Profile.objects.create(user=user, role=role, adviser=adviser)
            request.session.cycle_key()
            request.session['draft_user'] = user.pk
        if user:
            token = issue_token(user)
            if token:
                request.session['demo_email_link'] = reverse('confirm', args=[token])
        messages.info(request, 'If this address is eligible, a connection link has been prepared. No email is sent in demonstration mode.')
        if request.session.get('draft_user'):
            return redirect('dashboard')
        return redirect('access')
    demo_people = User.objects.filter(username__endswith='@example.invalid', profile__verified=True).select_related('profile').order_by('pk') if settings.DEMO_MODE else []
    return render(request, 'access.html', {'form': form, 'adviser': adviser, 'demo_people': demo_people, 'email_link': request.session.get('demo_email_link')})

@require_POST
def demo_login(request, pk):
    if not settings.DEMO_MODE:
        forbid()
    user = get_object_or_404(User, pk=pk, username__endswith='@example.invalid', profile__verified=True)
    request.session.flush()
    login(request, user)
    return redirect('dashboard')

@never_cache
def confirm(request, token):
    if request.method == 'POST':
        user = consume_token(token)
        if not user:
            messages.error(request, 'This link has expired or has already been used. Request a new link.')
            return redirect('access')
        request.session.flush()
        login(request, user)
        messages.success(request, 'Email confirmed.')
        return redirect('dashboard')
    return render(request, 'confirm.html')

@require_POST
def sign_out(request):
    logout(request)
    return redirect('access')

@require_identity
def dashboard(request):
    user = request.me_user
    return render(request, 'dashboard.html', {'offers': Offer.objects.filter(employer=user), 'candidate': Candidate.objects.filter(user=user).first(), 'matches': Match.objects.filter(offer__adviser=user), 'email_link': request.session.get('demo_email_link')})
