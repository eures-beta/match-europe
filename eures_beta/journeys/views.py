from eures_beta.documents.services import extract_pdf
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from eures_beta.accounts.access_control import identity, require_identity, forbid

from eures_beta.documents.forms import UploadForm
from eures_beta.candidates.models import Candidate
from eures_beta.offers.models import Offer


def interface(request):
    from eures_beta.journeys.demo import shared_notice

    user = identity(request)
    return {
        'me_user': user,
        'demo_mode': settings.DEMO_MODE,
        'shared_demo_notice': shared_notice(),
        'notifications': user.notifications.order_by('-created')[:8] if user else [],
    }


@never_cache
def home(request):
    if settings.DEMO_MODE:
        return redirect('/employer/pages/fr.html')
    return render(request, 'home.html')


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
                title = next(
                    (line.strip() for line in doc.text.splitlines() if line.strip()), ''
                )[:125]
                offer = Offer.objects.create(
                    employer=user,
                    adviser=user.profile.adviser,
                    document=doc,
                    title=title,
                    description=doc.text,
                )
                return redirect('offer', pk=offer.pk)
            Candidate.objects.create(
                user=user, document=doc, name='', experience=doc.text[:12000]
            )
            return redirect('candidate_edit')
    return render(
        request,
        'upload.html',
        {'form': form, 'email_link': request.session.get('demo_email_link')},
    )


def manifest(request):
    return JsonResponse(
        {
            'name': 'Match Europe',
            'short_name': 'Match Europe',
            'start_url': '/',
            'scope': '/',
            'display': 'standalone',
            'theme_color': '#003399',
            'background_color': '#f5f7fb',
            'icons': [
                {
                    'src': '/static/icon.svg',
                    'sizes': 'any',
                    'type': 'image/svg+xml',
                    'purpose': 'any',
                }
            ],
        },
        content_type='application/manifest+json',
    )


def service_worker(request):
    response = HttpResponse(
        (settings.APPS_DIR / 'static' / 'sw.js').read_text(),
        content_type='application/javascript',
    )
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response
