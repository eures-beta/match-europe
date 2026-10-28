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
