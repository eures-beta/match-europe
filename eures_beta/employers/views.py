from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from eures_beta.accounts.access_control import require_identity, forbid
from eures_beta.employers.forms import ImportAssignmentForm
from eures_beta.employers.models import EmployerImport


@require_identity
def imported_offer(request, pk):
    """Reuse authenticated staff workspaces; never expose session drafts to candidates."""
    user = request.me_user
    if (
        not user.is_active
        or not user.profile.verified
        or user.profile.role not in ('adviser', 'admin')
    ):
        forbid()
    qs = (
        EmployerImport.objects.all()
        if user.profile.role == 'admin'
        else EmployerImport.objects.filter(adviser=user)
    )
    obj = get_object_or_404(qs.select_related('adviser__profile'), pk=pk)
    form = (
        ImportAssignmentForm(
            request.POST if request.method == 'POST' else None,
            initial={'adviser': obj.adviser_id},
        )
        if user.profile.role == 'admin'
        else None
    )
    if request.method == 'POST':
        if form is None:
            forbid()
        if form.is_valid():
            obj.adviser = form.cleaned_data['adviser']
            obj.save(update_fields=['adviser', 'updated'])
            messages.success(request, _('Adviser assignment saved.'))
            return redirect('imported_offer', pk=obj.pk)
    elif request.method != 'GET':
        return HttpResponse(status=405)
    return render(
        request, 'imported_offer.html', {'imported': obj, 'assignment_form': form}
    )
