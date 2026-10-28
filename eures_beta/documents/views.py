from django.http import FileResponse
from django.shortcuts import get_object_or_404
from eures_beta.accounts.access_control import require_identity, forbid
from eures_beta.documents.models import Document


@require_identity
def document(request, pk):
    obj = get_object_or_404(Document, pk=pk)
    # Original PDFs are accessible only to their uploader in this first version.
    if obj.owner_id != request.me_user.pk:
        forbid()
    response = FileResponse(
        obj.file.open('rb'),
        as_attachment=True,
        filename='document.pdf',
        content_type='application/pdf',
    )
    response['Cache-Control'] = 'no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


from eures_beta.documents.services import extract_pdf
from django.shortcuts import redirect, render
from eures_beta.accounts.access_control import require_identity, forbid
from eures_beta.documents.forms import UploadForm
from eures_beta.candidates.models import Candidate
from eures_beta.offers.models import Offer


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
