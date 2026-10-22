"""Employer offer workspace; explicit memberships, no external submission."""
from copy import deepcopy
from functools import wraps
from django import forms
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from . import employer_login
from .employer_api import clean_data
from .employer_ownership import identity, memberships, accessible_imports
from .forms import EmployerContactForm, MOBILITY
from .models import EmployerImport
from .offer_ingestion import ImportFailure


def connected(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not identity(request) or not request.session.get('employer_verified_email'):
            return redirect('employer_access')
        lang = request.GET.get('lang', request.session.get('employer_auth_language', 'fr'))
        lang = lang if lang in ('fr','en','de') else 'fr'
        request.session['employer_auth_language'] = lang
        with translation.override(lang):
            return view(request, *args, **kwargs)
    return employer_login.enabled(wrapped)


def render(request, stage, status=200, **context):
    response = employer_login.page(request, stage, **context)
    response.status_code = status
    return response


def visible(request):
    # New account pages exclude anonymous legacy drafts, even in the same browser.
    return accessible_imports(request).filter(company__isnull=False).select_related('company')


class OfferEditForm(forms.Form):
    revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    title = forms.CharField(label=_('Job title'), max_length=125, required=False)
    companyName = forms.CharField(label=_('Company'), max_length=100, required=False,
        help_text=_('Changing this text does not change the establishment or access rights.'))
    city = forms.CharField(label=_('Workplace'), max_length=150, required=False)
    contractType = forms.ChoiceField(label=_('Contract'), required=False, choices=[('', _('Please choose')),
        ('PERMANENT_CONTRACT', _('Permanent contract')), ('FIXED_TERM_CONTRACT', _('Fixed-term contract')),
        ('TEMPORARY_WORK', _('Temporary work')), ('INTERNSHIP', _('Internship')),
        ('APPRENTICESHIP', _('Apprenticeship')), ('FREELANCE', _('Freelance')), ('TRAINING', _('Training'))])
    description = forms.CharField(label=_('Job description'), max_length=16000, required=False, widget=forms.Textarea(attrs={'rows':8}))
    desiredProfile = forms.CharField(label=_('Skills and experience sought'), max_length=4000, required=False, widget=forms.Textarea(attrs={'rows':5}))
    crossBorder = forms.ChoiceField(label=_('Do you accept candidates who keep living in a neighbouring country?'), choices=MOBILITY, required=False)
    relocation = forms.ChoiceField(label=_('Do you accept candidates who move from another country for this job?'), choices=MOBILITY, required=False)

    def __init__(self, *args, offer, **kwargs):
        self.offer = offer
        super().__init__(*args, initial={**offer.data, 'revision':offer.revision}, **kwargs)
        labels = {'salary':_('Salary'), 'hours':_('Working hours'), 'startDate':_('Start date'),
                  'frenchLevel':_('Languages and levels'), 'experience':_('Experience'), 'commute':_('Access to the workplace')}
        for key, label in labels.items():
            self.fields['clarify_'+key] = forms.CharField(label=label, max_length=1000, required=False,
                initial=offer.data.get('clarifications', {}).get(key, ''))
        choices = {
            'workConditions': [('early',_('Early hours')),('night',_('Night work')),('weekend',_('Weekends')),
                ('variable',_('Variable hours')),('shift',_('Shift work')),('physical',_('Physical work')),
                ('standing',_('Standing work')),('outdoor',_('Outdoor work')),('travel',_('Frequent travel')),
                ('none',_('None')),('unknown',_('To discuss'))],
            'permits':[(x,x) for x in ('B','C','CE','D','DE','CACES')]+[('other',_('Other'))],
            'arrivalAids':[('housing',_('Housing')),('admin',_('Administrative support')),('transport',_('Transport')),
                ('onboarding',_('Onboarding')),('other',_('Other')),('none',_('None')),('unknown',_('To discuss'))]}
        req = offer.data.get('requirements', {})
        for key, label in [('workConditions',_('Working conditions')),('permits',_('Driving licences and authorisations')),('arrivalAids',_('Arrival support'))]:
            self.fields[key] = forms.MultipleChoiceField(label=label, choices=choices[key], required=False,
                initial=req.get(key, []), widget=forms.CheckboxSelectMultiple)
        self.fields['permitRequired'] = forms.ChoiceField(label=_('Is a licence or authorisation required?'), choices=MOBILITY[:3], required=False, initial=req.get('permitRequired',''))
        for key, label in [('permitOther',_('Other authorisation')),('aidOther',_('Other arrival support'))]:
            self.fields[key] = forms.CharField(label=label, required=False, max_length=500, initial=req.get(key,''))
        self.order_fields(['revision','title','companyName','city','contractType','description','desiredProfile',
            *['clarify_'+key for key in labels], 'workConditions','permitRequired','permits','permitOther',
            'crossBorder','relocation','arrivalAids','aidOther'])

    def clean(self):
        values = super().clean()
        if self.errors:
            return values
        if values.get('permits') and values.get('permitRequired') != 'yes':
            self.add_error('permitRequired', _('Select Yes before choosing required licences or authorisations.'))
            return values
        data = deepcopy(self.offer.data)
        for key in ('title','companyName','city','contractType','description','desiredProfile','crossBorder','relocation'):
            data[key] = values[key]
        data.setdefault('clarifications', {}).update({key[8:]:val for key,val in values.items() if key.startswith('clarify_')})
        data['requirements'] = {key:values[key] for key in ('workConditions','permits','arrivalAids','permitRequired','permitOther','aidOther')}
        try:
            cleaned = clean_data(data)
        except ImportFailure:
            raise forms.ValidationError(_('Choose either specific conditions or None / To discuss, not both.')) from None
        # Preserve provenance and other original metadata, never accept it from the form.
        data.update(cleaned)
        if data.get('geo', {}).get('query') != data.get('city'):
            data.pop('geo', None)
        self.offer_data = data
        return values


@connected
@require_GET
def offers(request):
    companies = [member.company for member in memberships(request).select_related('company').order_by('company__name','company_id')]
    selected = request.GET.get('company', '')
    rows = visible(request)
    if selected:
        if not selected.isdecimal() or int(selected) not in [c.pk for c in companies]:
            raise Http404
        rows = rows.filter(company_id=selected)
    private = EmployerImport.objects.filter(company__isnull=True, created_by=identity(request)).order_by('-updated')
    return render(request, 'offers', companies=companies, selected=selected,
        offers=Paginator(rows.order_by('-updated','pk'), 20).get_page(request.GET.get('page')),
        private_drafts=private, workspace=True)


@connected
@require_GET
def detail(request, id):
    offer = get_object_or_404(visible(request), pk=id)
    form = OfferEditForm(offer=offer)
    rows = []
    for field in form:
        if field.name in ('revision','title'):
            continue
        value = field.value()
        choices = dict(getattr(field.field, 'choices', []))
        if isinstance(value, (list, tuple)):
            value = ', '.join(str(choices.get(item, item)) for item in value)
        elif choices and value:
            value = choices.get(value, value)
        if value:
            rows.append((field.label, value))
    return render(request, 'offer_detail', offer=offer, saved=request.GET.get('saved')=='1',
        fields=rows, contact=EmployerContactForm(initial=offer.contact), workspace=True)


@connected
@require_http_methods(['GET', 'POST'])
def edit(request, id):
    with transaction.atomic():
        offer = get_object_or_404(visible(request).select_for_update(of=('self',)), pk=id)
        if offer.search_started_at:
            return render(request, 'offer_locked', status=409 if request.method=='POST' else 200, offer=offer, workspace=True)
        form = OfferEditForm(request.POST if request.method=='POST' else None, offer=offer)
        contact = EmployerContactForm(request.POST if request.method=='POST' else None, initial=offer.contact, prefix='contact')
        if request.method=='POST':
            valid = form.is_valid() & contact.is_valid()
            if valid and form.cleaned_data['revision'] != offer.revision:
                form.add_error(None, _('A colleague changed this offer. Your changes have not been saved. Open the current version before trying again.'))
            elif valid:
                offer.data = form.offer_data
                offer.contact = contact.cleaned_data
                offer.revision += 1
                offer.validated_at = offer.synced_at = None
                offer.sandbox_response = {}
                offer.save(update_fields=['data','contact','revision','validated_at','synced_at','sandbox_response','updated'])
                from django.urls import reverse
                return redirect(reverse('employer_offer', args=[offer.pk])+'?saved=1')
    return render(request, 'offer_edit', offer=offer, form=form, contact=contact, workspace=True)


@connected
@require_POST
def duplicate(request, id):
    with transaction.atomic():
        original = get_object_or_404(visible(request).select_for_update(of=('self',)), pk=id)
        if request.POST.get('revision') != str(original.revision):
            return render(request, 'offer_conflict', status=409, offer=original, workspace=True)
        # Explicit action, new UUID, no publication/search state or external identifier copied.
        data = clean_data(deepcopy(original.data))
        copy = EmployerImport.objects.create(company=original.company, created_by=identity(request),
            duplicated_from=original, session_key='', email=identity(request).email,
            contact=deepcopy(original.contact), preparation_agreed_at=timezone.now(),
            source_kind='manual', source_url='', data=data)
    return redirect('employer_offer_edit', id=copy.pk)


@connected
@require_POST
def resume_attachment(request, id):
    offer = get_object_or_404(EmployerImport, pk=id, company__isnull=True, created_by=identity(request))
    request.session['employer_claim_import'] = str(offer.pk)
    return redirect('employer_connected')
