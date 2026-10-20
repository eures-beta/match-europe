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


from django.utils.translation import gettext as _


from django.views.decorators.cache import never_cache


from django.views.decorators.http import require_POST


from .forms import ImportAssignmentForm, AccessForm, CandidateForm, MessageForm, OfferForm, QuestionForm, ReviewForm, UploadForm


from .models import EmployerImport, Answer, Candidate, Conversation, Document, Event, Match, Message, Notification, Offer, Profile, Question


from .services import adviser_from, audit, consume_token, dispatch_offer, extract_pdf, invite_for, issue_token, notify, suggest_candidates


def interface(request):
    user = identity(request)
    return {'me_user': user, 'demo_mode': settings.DEMO_MODE,
            'notifications': user.notifications.order_by('-created')[:8] if user else []}


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
    return user.pk == offer.employer_id or (user.profile.verified and
           (user.pk == offer.adviser_id or user.profile.role == 'admin'))


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
        if not user and adviser and role in ['employer', 'candidate']:
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
                # Demo only: link visible exclusively in the requesting browser session.
                request.session['demo_email_link'] = reverse('confirm', args=[token])
        messages.info(request, _('If this address is eligible, a connection link has been prepared. No email is sent in demonstration mode.'))
        if request.session.get('draft_user'):
            return redirect('upload')
        return redirect('access')
    demo_people = User.objects.filter(username__endswith='@example.invalid', profile__verified=True).select_related('profile').order_by('pk') if settings.DEMO_MODE else []
    return render(request, 'access.html', {'form': form, 'adviser': adviser, 'demo_people': demo_people,
                                         'email_link': request.session.get('demo_email_link')})


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
            messages.error(request, _('This link has expired or has already been used. Request a new link.'))
            return redirect('access')
        request.session.flush()
        login(request, user)
        messages.success(request, _('Email confirmed.'))
        return redirect('dashboard')
    # GET does not consume the token, avoiding email scanner activation.
    return render(request, 'confirm.html')


@require_POST
def sign_out(request):
    logout(request)
    return redirect('access')


@require_identity
def dashboard(request):
    user = request.me_user
    role = user.profile.role
    offers = Offer.objects.none()
    matches = Match.objects.none()
    candidate = None
    invitation = None
    if role == 'employer':
        offers = Offer.objects.filter(employer=user)
        matches = Match.objects.filter(offer__employer=user, state__in=['review', 'clarify', 'introduced'])
    elif role == 'candidate':
        candidate = Candidate.objects.filter(user=user).first()
        matches = Match.objects.filter(candidate__user=user).exclude(state='suggested')
    elif role in ['adviser', 'admin'] and user.profile.verified:
        offers = Offer.objects.all() if role == 'admin' else Offer.objects.filter(adviser=user)
        matches = Match.objects.filter(offer__in=offers)
        if role == 'adviser':
            invitation = invite_for(user)
    else:
        forbid()
    return render(request, 'dashboard.html', {'offers': offers.order_by('-created'), 'matches': matches.select_related('offer', 'candidate'),
                  'candidate': candidate, 'invitation': invitation,
                  'email_link': request.session.get('demo_email_link'),
                  'events': Event.objects.order_by('-created')[:30] if role == 'admin' else [],
                  'people': Profile.objects.select_related('user') if role == 'admin' else []})


@require_identity
def upload(request):
    user = request.me_user
    role = user.profile.role
    if role not in ['employer', 'candidate'] or not user.profile.adviser_id:
        forbid()
    if role == 'candidate' and Candidate.objects.filter(user=user).exists():
        return redirect('candidate_edit')
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            doc = extract_pdf(form.cleaned_data['document'], user)
        except ValueError as exc:
            form.add_error('document', str(exc))
        else:
            if role == 'employer':
                title = next((line.strip() for line in doc.text.splitlines() if line.strip()), '')[:125]
                offer = Offer.objects.create(employer=user, adviser=user.profile.adviser, document=doc,
                                             title=title, description=doc.text)
                return redirect('offer', pk=offer.pk)
            Candidate.objects.create(user=user, document=doc, name='', experience=doc.text[:12000])
            return redirect('candidate_edit')
    return render(request, 'upload.html', {'form': form, 'email_link': request.session.get('demo_email_link')})


@require_identity
def offer(request, pk):
    user = request.me_user
    obj = get_object_or_404(Offer, pk=pk)
    if not allowed_offer(user, obj):
        forbid()
    editable = obj.employer_id == user.pk and obj.state == Offer.State.DRAFT
    form = OfferForm(request.POST if request.method == 'POST' and request.POST.get('action') in ['save', 'validate'] else None,
                     instance=obj, complete=request.POST.get('action') == 'validate')
    question_form = QuestionForm(request.POST if request.method == 'POST' and request.POST.get('action') == 'question' else None)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ['save', 'validate', 'question', 'remove_question']:
            if not editable:
                forbid()
            if action == 'question' and question_form.is_valid():
                q = question_form.save(commit=False)
                q.offer = obj
                q.position = obj.questions.count()
                q.save()
                audit(user, 'question_added', q)
                return redirect('offer', pk=pk)
            if action == 'remove_question':
                get_object_or_404(Question, pk=request.POST.get('question'), offer=obj).delete()
                return redirect('offer', pk=pk)
            if action in ['save', 'validate'] and form.is_valid():
                with transaction.atomic():
                    obj = form.save()
                    if action == 'validate':
                        if not request.POST.get('agreement'):
                            form.add_error(None, _('Please confirm that the offer and questions are ready for matching.'))
                        else:
                            obj.validated_at = timezone.now()
                            obj.state = Offer.State.PENDING if not user.profile.verified else Offer.State.READY
                            obj.save()
                            audit(user, 'offer_validated', obj)
                            if user.profile.verified:
                                dispatch_offer(obj, user)
                            return redirect('offer', pk=pk)
                    else:
                        messages.success(request, _('Draft saved.'))
                        return redirect('offer', pk=pk)
        elif action == 'suggest':
            if user.pk != obj.adviser_id and user.profile.role != 'admin':
                forbid()
            try:
                suggest_candidates(obj, user)
            except ValueError as exc:
                messages.error(request, str(exc))
            return redirect('offer', pk=pk)
        else:
            forbid()
    visible_matches = obj.matches.select_related('candidate') if user.pk == obj.adviser_id or user.profile.role == 'admin' else []
    return render(request, 'offer.html', {'offer': obj, 'form': form, 'question_form': question_form, 'editable': editable,
                  'matches': visible_matches, 'email_link': request.session.get('demo_email_link')})


@require_identity
def candidate_edit(request):
    user = request.me_user
    if user.profile.role != 'candidate':
        forbid()
    obj = get_object_or_404(Candidate, user=user)
    form = CandidateForm(request.POST or None, instance=obj, complete=request.POST.get('action') == 'validate')
    if request.method == 'POST' and form.is_valid():
        if request.POST.get('action') not in ['save', 'validate']:
            forbid()
        if obj.sent_at:
            forbid()
        obj = form.save()
        if request.POST.get('action') == 'validate':
            if not request.POST.get('agreement'):
                form.add_error(None, _('Please agree to matching and confirm your profile.'))
            else:
                obj.validated_at = timezone.now()
                obj.sent_at = timezone.now() if user.profile.verified else None
                obj.save()
                audit(user, 'candidate_validated', obj)
                return redirect('dashboard')
        else:
            messages.success(request, _('Draft saved.'))
            return redirect('candidate_edit')
    return render(request, 'candidate.html', {'candidate': obj, 'form': form, 'email_link': request.session.get('demo_email_link')})


@require_identity
def match_detail(request, pk):
    user = request.me_user
    obj = get_object_or_404(Match.objects.select_related('candidate__user', 'offer__employer', 'offer__adviser'), pk=pk)
    if not allowed_match(user, obj) or (user.pk == obj.candidate.user_id and obj.state == Match.State.SUGGESTED):
        forbid()
    is_candidate = user.pk == obj.candidate.user_id
    is_employer = user.pk == obj.offer.employer_id
    is_adviser = user.pk == obj.offer.adviser_id
    if request.method == 'POST':
        action = request.POST.get('action')
        with transaction.atomic():
            obj = Match.objects.select_for_update().get(pk=pk)
            if action == 'invite' and is_adviser and obj.state == Match.State.SUGGESTED:
                obj.state = Match.State.INVITED
                notify(obj.candidate.user, 'An offer is waiting for you', reverse('match', args=[pk]))
            elif action == 'interested' and is_candidate and obj.state == Match.State.INVITED:
                obj.state = Match.State.ANSWERING
            elif action == 'decline' and is_candidate and obj.state in [Match.State.INVITED, Match.State.ANSWERING, Match.State.CLARIFY]:
                obj.state = Match.State.DECLINED
                notify(obj.offer.adviser, 'Candidate response received', reverse('match', args=[pk]))
            elif action in ['save_answers', 'submit_answers'] and is_candidate and obj.state in [Match.State.ANSWERING, Match.State.CLARIFY]:
                responses = []
                for question in obj.offer.questions.all():
                    choice = request.POST.get(f'choice_{question.pk}', '').strip()
                    text = request.POST.get(f'text_{question.pk}', '').strip()
                    if (choice and choice not in question.choices()) or len(text) > 4000:
                        return HttpResponse(_('Invalid answer.'), status=400)
                    responses.append((question, choice, text))
                if action == 'submit_answers' and (any(not c and not t for q, c, t in responses) or not request.POST.get('agreement')):
                    messages.error(request, _('Answer each question or explain what needs clarification, and confirm your agreement to introduction.'))
                    return redirect('match', pk=pk)
                for question, choice, text in responses:
                    Answer.objects.update_or_create(match=obj, question=question, defaults={'choice': choice, 'text': text})
                if action == 'submit_answers':
                    obj.candidate_agreement = True
                    obj.state = Match.State.REVIEW
                    notify(obj.offer.adviser, 'Prequalification ready for review', reverse('match', args=[pk]))
                    notify(obj.offer.employer, 'Prequalification ready for review', reverse('match', args=[pk]))
            elif action == 'employer_agree' and is_employer and obj.state == Match.State.REVIEW:
                if not request.POST.get('agreement'):
                    return HttpResponse(_('Agreement required.'), status=400)
                obj.employer_agreement = True
            elif action == 'clarify' and is_adviser and obj.state == Match.State.REVIEW:
                note = request.POST.get('note', '').strip()[:2000]
                if not note:
                    return HttpResponse(_('Please explain what needs clarification.'), status=400)
                obj.review_note = note
                obj.state = Match.State.CLARIFY
                obj.candidate_agreement = False
                obj.employer_agreement = False
                notify(obj.candidate.user, 'Clarification requested', reverse('match', args=[pk]))
            elif action == 'introduce' and is_adviser and obj.state == Match.State.REVIEW:
                if not obj.candidate_agreement or not obj.employer_agreement:
                    messages.error(request, _('Both participants must agree before the conversation is opened.'))
                    return redirect('match', pk=pk)
                note = request.POST.get('note', '').strip()[:2000]
                if not note:
                    return HttpResponse(_('Write an introduction message.'), status=400)
                conv = Conversation.objects.create(match=obj, opened_by=user)
                Message.objects.create(conversation=conv, sender=user, body=note)
                obj.state = Match.State.INTRODUCED
                for recipient in [obj.candidate.user, obj.offer.employer]:
                    notify(recipient, 'Your conversation is open', reverse('conversation', args=[conv.pk]))
            else:
                forbid()
            obj.save()
            audit(user, action, obj)
        return redirect('match', pk=pk)
    answers = {a.question_id: a for a in obj.answers.all()}
    questions = [{'q': q, 'answer': answers.get(q.pk), 'choices': q.choices()} for q in obj.offer.questions.all()]
    return render(request, 'match.html', {'match': obj, 'questions': questions, 'is_candidate': is_candidate,
                  'is_employer': is_employer, 'is_adviser': is_adviser, 'review_form': ReviewForm()})


def conversation_allowed(user, conv):
    # Operators do not receive blanket access to private conversations.
    return user.profile.verified and user.pk in [conv.match.candidate.user_id, conv.match.offer.employer_id, conv.match.offer.adviser_id]


@require_identity
def conversation(request, pk):
    obj = get_object_or_404(Conversation.objects.select_related('match__candidate__user', 'match__offer__employer', 'match__offer__adviser'), pk=pk)
    user = request.me_user
    if not conversation_allowed(user, obj):
        forbid()
    form = MessageForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        msg = Message.objects.create(conversation=obj, sender=user, body=form.cleaned_data['body'])
        audit(user, 'message_sent', msg)
        for recipient in [obj.match.candidate.user, obj.match.offer.employer, obj.match.offer.adviser]:
            if recipient.pk != user.pk:
                notify(recipient, 'New message', reverse('conversation', args=[pk]))
        return redirect('conversation', pk=pk)
    return render(request, 'conversation.html', {'conversation': obj, 'form': form, 'chat_messages': obj.messages.select_related('sender__profile')})


@require_identity
def conversation_feed(request, pk):
    obj = get_object_or_404(Conversation, pk=pk)
    if not conversation_allowed(request.me_user, obj):
        forbid()
    return JsonResponse({'count': obj.messages.count(), 'latest': obj.messages.order_by('-pk').values_list('pk', flat=True).first()})


@require_identity
def document(request, pk):
    obj = get_object_or_404(Document, pk=pk)
    # Original PDFs are accessible only to their uploader in this first version.
    if obj.owner_id != request.me_user.pk:
        forbid()
    response = FileResponse(obj.file.open('rb'), as_attachment=True, filename='document.pdf', content_type='application/pdf')
    response['Cache-Control'] = 'no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@require_POST
@require_identity
def read_notifications(request):
    request.me_user.notifications.filter(read=False).update(read=True)
    return redirect('dashboard')


def manifest(request):
    return JsonResponse({'name': 'Match Europe', 'short_name': 'Match Europe', 'start_url': '/', 'scope': '/',
                         'display': 'standalone', 'theme_color': '#003399', 'background_color': '#f5f7fb',
                         'icons': [{'src': '/static/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any'}]},
                        content_type='application/manifest+json')


def service_worker(request):
    response = HttpResponse((settings.BASE_DIR / 'static' / 'sw.js').read_text(), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


