"""Loopback-only sandbox workflow. PostgreSQL drafts are session-owned; CSRF remains enabled."""
import json
import math
import os
import time
import threading
import secrets
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction, connection
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from .models import EmployerImport
from .forms import EmployerContactForm
from .offer_ingestion import ImportFailure, empty_data, fetch_public, parse_page, read_pdf, read_url

ROOT=Path(__file__).resolve().parents[2]
lock=threading.Lock()
last_geocode=0.0


def local_only(view):
    @wraps(view)
    @never_cache
    def wrapped(request,*args,**kwargs):
        if not settings.DEMO_MODE or request.META.get('REMOTE_ADDR') not in ('127.0.0.1','::1') or os.environ.get('ME_EMPLOYER_LOCAL_API')!='1':
            raise Http404()
        return view(request,*args,**kwargs)
    return wrapped


@local_only
@ensure_csrf_cookie
def preview(request,path):
    base=ROOT/'previews'/'employer-landing'
    candidate=(base/path).resolve()
    if not candidate.is_relative_to(base.resolve()) or not candidate.is_file() or candidate.suffix not in ('.html','.js','.png','.svg','.jpg'):
        raise Http404()
    if candidate.suffix=='.html':
        # Static build templates remain usable; served HTML activates the real same-origin API.
        body=candidate.read_text().replace('<body>','<body data-live-local="true">')
        return HttpResponse(body)
    return FileResponse(candidate.open('rb'))


@local_only
def historical_css(request):
    return FileResponse((ROOT/'forms/eures-beta/site.css').open('rb'),content_type='text/css')


def failure(code,status=400): return JsonResponse({'error':code},status=status)


def body(request):
    if len(request.body)>100000: raise ImportFailure('invalid_data')
    try: value=json.loads(request.body)
    except (ValueError,UnicodeError): raise ImportFailure('invalid_data') from None
    if not isinstance(value,dict): raise ImportFailure('invalid_data')
    return value


@local_only
def read_source(request):
    if request.method!='POST': return failure('method',405)
    if request.POST.get('agreement')!='true': return failure('agreement_required')
    try:
        url=request.POST.get('url','').strip()
        kind=request.POST.get('kind','url')
        if kind=='pdf':
            upload=request.FILES.get('document')
            if not upload: raise ImportFailure('missing')
            data=read_pdf(upload);final=''
        elif kind=='url':
            data,final=read_url(url)
        else: raise ImportFailure('invalid_data')
        token=secrets.token_urlsafe(24)
        request.session['pending_offer_source']={'kind':kind,'token':token,'url':url,'final':final,'data':data,'at':time.time()}
        return JsonResponse({'token':token})
    except ImportFailure as exc: return failure(exc.code)


def clean_contact(value):
    if not isinstance(value,dict): raise ImportFailure('invalid_contact')
    form=EmployerContactForm(value)
    if not form.is_valid(): raise ImportFailure('invalid_contact')
    return form.cleaned_data


@local_only
def imports(request,id=None):
    if request.method=='GET':
        if not request.session.session_key: return failure('not_found',404) if id else JsonResponse({'drafts':[]})
        qs=EmployerImport.objects.filter(session_key=request.session.session_key)
        if id:
            obj=qs.filter(pk=id).first()
            if not obj: return failure('not_found',404)
            return JsonResponse(serialize(obj))
        return JsonResponse({'drafts':[{'id':str(x.id),'title':x.data.get('title',''),'updated':x.updated.isoformat(),'synced':bool(x.synced_at)} for x in qs.order_by('-updated')[:30]]})
    if request.method!='POST': return failure('method',405)
    try:
        if not request.session.session_key: request.session.create()
        if id:
            obj=EmployerImport.objects.filter(pk=id,session_key=request.session.session_key).first()
            if not obj: return failure('not_found',404)
            payload=body(request)
            return update(request,obj,payload)
        email=request.POST.get('email','').strip()
        try: validate_email(email)
        except ValidationError: raise ImportFailure('invalid_email') from None
        if len(email)>254 or request.POST.get('agreement')!='true': raise ImportFailure('agreement_required')
        if EmployerImport.objects.filter(session_key=request.session.session_key).count()>=30: raise ImportFailure('limit')
        try: contact=clean_contact(json.loads(request.POST.get('contact','{}')))
        except (ValueError,TypeError): raise ImportFailure('invalid_contact') from None
        kind=request.POST.get('kind');source=''
        if kind=='url':
            source=request.POST.get('url','').strip()
            pending=request.session.get('pending_offer_source',{})
            if pending.get('kind','url')!='url' or pending.get('token')!=request.POST.get('sourceToken') or pending.get('url')!=source or time.time()-pending.get('at',0)>900:
                raise ImportFailure('unreadable_url')
            data=pending['data'];source=pending['final']
        elif kind=='pdf':
            pending=request.session.get('pending_offer_source',{})
            if pending.get('kind')!='pdf' or pending.get('token')!=request.POST.get('sourceToken') or time.time()-pending.get('at',0)>900:
                raise ImportFailure('unreadable')
            data=pending['data']
        elif kind=='manual':
            text=request.POST.get('text','').strip()
            if not text or len(text)>16000: raise ImportFailure('invalid_data')
            data=empty_data();data['description']=text;data['extraction']='manual'
        else: raise ImportFailure('invalid_data')
        obj=EmployerImport.objects.create(session_key=request.session.session_key,email=email,contact=contact,preparation_agreed_at=timezone.now(),source_kind=kind,source_url=source,data=data)
        if kind in ('url','pdf'): request.session.pop('pending_offer_source',None)
        return initial_send(obj,created=True)
    except ImportFailure as exc: return failure(exc.code)


def serialize(obj):
    return {'id':str(obj.id),'contact':{'email':obj.email,**obj.contact},'data':obj.data,'revision':obj.revision,'source':obj.source_url,'kind':obj.source_kind,
            'synced':bool(obj.synced_at),'sandbox':obj.sandbox_response,
            'stage':'review' if obj.initial_sent_at else 'prepare'}


def initial_send(obj,created=False):
    data=obj.data
    if not all(data.get(k) for k in ('title','companyName','city','description')):
        return JsonResponse(serialize(obj),status=201 if created else 200)
    try:
        geo=data.get('geo')
        if not geo or geo.get('query')!=data['city']: geo=geocode(data['city'])
        data['geo']=geo
        post={'id':str(obj.id),'title':data['title'],'companyName':data['companyName'],'description':data['description'],
              'desiredProfile':data.get('desiredProfile',''),'workplaceLocation':{'city':data['city'][:50],'latitude':geo['latitude'],'longitude':geo['longitude']},
              'createdAt':obj.created.isoformat(),'active':False}
        if data.get('contractType'): post['contractType']=data['contractType']
        aglae('POST','job-posting',{'jobPostings':[post]})
        returned=aglae('GET',f'job-posting/{obj.id}')
        if returned.get('id')!=str(obj.id) or returned.get('active') is not False: raise ImportFailure('sandbox_error')
        for key in ('title','companyName','description','desiredProfile','contractType'):
            if returned.get(key) is not None: data[key]=returned[key]
        # Keep full source address and geocoding provenance rather than the API's 50-character city limit.
        obj.data=data;obj.sandbox_response=returned;obj.initial_sent_at=timezone.now();obj.revision+=1;obj.save()
        return JsonResponse(serialize(obj),status=201 if created else 200)
    except ImportFailure as exc:
        obj.data=data;obj.save()
        return JsonResponse({'error':exc.code,**serialize(obj)},status=502)


CONTRACTS={'PERMANENT_CONTRACT','FIXED_TERM_CONTRACT','TEMPORARY_WORK','INTERNSHIP','APPRENTICESHIP','FREELANCE','TRAINING'}


def clean_data(raw):
    if not isinstance(raw,dict): raise ImportFailure('invalid_data')
    out=empty_data()
    for key,limit in {'title':125,'companyName':100,'city':150,'contractType':32,'description':16000,'desiredProfile':4000}.items():
        value=raw.get(key,'')
        if not isinstance(value,str) or len(value)>limit: raise ImportFailure('invalid_data')
        out[key]=value.strip()
    if out['contractType'] and out['contractType'] not in CONTRACTS: raise ImportFailure('invalid_data')
    clar=raw.get('clarifications',{})
    if not isinstance(clar,dict): raise ImportFailure('invalid_data')
    for key in out['clarifications']:
        value=clar.get(key,'')
        if not isinstance(value,str) or len(value)>1000: raise ImportFailure('invalid_data')
        out['clarifications'][key]=value.strip()
    req=raw.get('requirements',{})
    if not isinstance(req,dict): raise ImportFailure('invalid_data')
    allowed={'workConditions':{'early','night','weekend','variable','shift','physical','standing','outdoor','travel','none','unknown'},
             'permits':{'B','C','CE','D','DE','CACES','other'},
             'arrivalAids':{'housing','admin','transport','onboarding','other','none','unknown'}}
    for key,options in allowed.items():
        values=req.get(key,[])
        if not isinstance(values,list) or len(values)>len(options) or any(not isinstance(v,str) or v not in options for v in values): raise ImportFailure('invalid_data')
        if key!='permits' and any(v in values for v in ('none','unknown')) and len(values)>1: raise ImportFailure('invalid_data')
        out['requirements'][key]=list(dict.fromkeys(values))
    value=req.get('permitRequired','')
    if value not in ('','yes','no'): raise ImportFailure('invalid_data')
    out['requirements']['permitRequired']=value
    for key in ('permitOther','aidOther'):
        value=req.get(key,'')
        if not isinstance(value,str) or len(value)>500: raise ImportFailure('invalid_data')
        out['requirements'][key]=value.strip()
    if out['requirements']['permitRequired']!='yes':
        out['requirements']['permits']=[];out['requirements']['permitOther']=''
    if 'other' not in out['requirements']['permits']: out['requirements']['permitOther']=''
    if 'other' not in out['requirements']['arrivalAids']: out['requirements']['aidOther']=''
    for key in ('crossBorder','relocation'):
        value=raw.get(key,'')
        if value not in ('','yes','no','discuss'): raise ImportFailure('invalid_data')
        out[key]=value
    questions=raw.get('questions',[])
    if not isinstance(questions,list) or len(questions)>20: raise ImportFailure('invalid_data')
    for q in questions:
        if not isinstance(q,dict) or not isinstance(q.get('question'),str) or not 1<=len(q['question'].strip())<=2000 or type(q.get('mandatory')) is not bool:
            raise ImportFailure('invalid_data')
        out['questions'].append({'question':q['question'].strip(),'mandatory':q['mandatory'],'humanReviewRequired':True})
    return out


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*a,**k): return None


def aglae(*args, **kwargs):
    raise ImportFailure('sandbox_unavailable')



def geocode(*args, **kwargs):
    raise ImportFailure('sandbox_unavailable')



def fetch_geocode(query):
    request=Request('https://nominatim.openstreetmap.org/search?'+query,headers={'User-Agent':'MatchEurope-LocalSandbox/1.0 (local employer import test)','Accept':'application/json'})
    with build_opener(NoRedirect).open(request,timeout=15) as r: return r.read(200000).decode(),None


def update(request,obj,payload):
    # PostgreSQL session advisory lock spans save + external write + readback.
    # It also serializes retries from another tab without storing API keys in the DB.
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_lock(hashtext(%s))',[str(obj.id)])
    try:
        return update_locked(request,obj,payload)
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(hashtext(%s))',[str(obj.id)])


def update_locked(request,obj,payload):
    action=payload.get('action')
    if action not in ('save','validate','locate','prepare','contact'): raise ImportFailure('invalid_data')
    if action=='contact':
        contact=clean_contact(payload.get('contact'))
        with transaction.atomic():
            obj=EmployerImport.objects.select_for_update().get(pk=obj.pk,session_key=request.session.session_key)
            if payload.get('revision')!=obj.revision: return failure('conflict',409)
            obj.contact=contact;obj.revision+=1;obj.save(update_fields=['contact','revision','updated'])
        return JsonResponse(serialize(obj))
    clean=clean_data(payload.get('data'))
    with transaction.atomic():
        obj=EmployerImport.objects.select_for_update().get(pk=obj.pk,session_key=request.session.session_key)
        if payload.get('revision')!=obj.revision: return failure('conflict',409)
        geo=obj.data.get('geo')
        if not geo or geo.get('query')!=clean['city']: geo=None
        clean['extraction']=obj.data.get('extraction','manual')
        if action=='locate': geo=geocode(clean['city'])
        if geo: clean['geo']=geo
        if action=='validate':
            clean_contact(obj.contact)
            if not obj.initial_sent_at: raise ImportFailure('initial_required')
            if payload.get('confirmed') is not True or not all(clean[k] for k in ('title','companyName','city','description','contractType')):
                raise ImportFailure('required')
            if not geo:
                geo=geocode(clean['city']);clean['geo']=geo
            # Save corrections before the API call, including if the sandbox later fails.
        obj.data=clean;obj.revision+=1;obj.validated_at=None;obj.synced_at=None;obj.sandbox_response={}
        obj.save()
    if action=='prepare': return initial_send(obj)
    if action!='validate': return JsonResponse(serialize(obj))
    # Record the validated version. Stable UUID makes a retry an update, not a duplicate creation.
    clarification='\n'.join(f'{k}: {v}' for k,v in clean['clarifications'].items() if v)
    clarification+='\nCross-border recruitment: '+(clean['crossBorder'] or 'unspecified')
    clarification+='\nRelocation recruitment: '+(clean['relocation'] or 'unspecified')
    clarification+='\nJob conditions, permits and arrival support: '+json.dumps(clean['requirements'],ensure_ascii=False)
    post={'id':str(obj.id),'title':clean['title'],'companyName':clean['companyName'],'description':clean['description'],
          'desiredProfile':clean['desiredProfile'],'workplaceLocation':{'city':clean['city'][:50],'latitude':geo['latitude'],'longitude':geo['longitude']},
          'contractType':clean['contractType'],'createdAt':obj.created.isoformat(),'active':False}
    if clarification: post['additionalAgentDescription']=('Match Europe sandbox. Human review required.\n'+clarification)[:4000]
    try:
        aglae('POST','job-posting',{'jobPostings':[post]})
        # Automatic exclusion deliberately disabled in the external qualification engine.
        # Essential flags remain local for human review; no qualification is started.
        questions=[{'kind':'standard','code':f'ME_Q_{i+1}','label':q['question'][:100],'question':q['question'],
                    'rank':i,'isMandatory':False,'evaluationGuideline':'Human review required. Do not reject automatically.'} for i,q in enumerate(clean['questions'])]
        aglae('PUT',f'job-posting/{obj.id}/specific-prerequisites',{'specificPrerequisites':questions})
        returned=aglae('GET',f'job-posting/{obj.id}')
    except ImportFailure as exc:
        return JsonResponse({'error':exc.code,**serialize(obj)},status=502)
    if returned.get('id')!=str(obj.id) or returned.get('active') is not False: return failure('sandbox_error',502)
    with transaction.atomic():
        current=EmployerImport.objects.select_for_update().get(pk=obj.pk)
        if current.revision!=obj.revision: return failure('conflict',409)
        current.validated_at=current.synced_at=timezone.now();current.sandbox_response=returned;current.save()
    return JsonResponse(serialize(current))
