from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from eures_beta.accounts.access_control import require_identity, forbid
from eures_beta.accounts.services import audit
from eures_beta.candidates.forms import CandidateForm
from eures_beta.candidates.models import Candidate


@require_identity
def candidate_edit(request):
    user = request.me_user
    if user.profile.role != 'candidate':
        forbid()
    obj = get_object_or_404(Candidate, user=user)
    form = CandidateForm(
        request.POST or None,
        instance=obj,
        complete=request.POST.get('action') == 'validate',
    )
    if request.method == 'POST' and form.is_valid():
        if request.POST.get('action') not in ['save', 'validate']:
            forbid()
        if obj.sent_at:
            forbid()
        obj = form.save()
        if request.POST.get('action') == 'validate':
            if not request.POST.get('agreement'):
                form.add_error(
                    None, _('Please agree to matching and confirm your profile.')
                )
            else:
                obj.validated_at = timezone.now()
                obj.sent_at = timezone.now() if user.profile.verified else None
                obj.save()
                audit(user, 'candidate_validated', obj)
                return redirect('dashboard')
        else:
            messages.success(request, _('Draft saved.'))
            return redirect('candidate_edit')
    return render(
        request,
        'candidate.html',
        {
            'candidate': obj,
            'form': form,
            'email_link': request.session.get('demo_email_link'),
        },
    )
