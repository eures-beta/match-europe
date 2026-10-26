"""Loopback-only, ephemeral Web Push diagnostic. Never enrolls an employer in the pilot."""
import base64
import json
import threading
from urllib.parse import urlsplit
from pathlib import Path
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .employer_api import local_only

_lock=threading.Lock()
_states={}

def key():
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    path=Path(__file__).resolve().parents[1]/'.runtime'/'push-test-vapid.pem'
    with _lock:
        if not path.exists():
            private=ec.generate_private_key(ec.SECP256R1())
            path.parent.mkdir(exist_ok=True)
            with path.open('xb') as handle:
                import os
                os.fchmod(handle.fileno(),0o600)
                handle.write(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        private=serialization.load_pem_private_key(path.read_bytes(),password=None)
    raw=private.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    return path,base64.urlsafe_b64encode(raw).decode().rstrip('=')

def subscription(value):
    if not isinstance(value,dict): raise ValueError()
    endpoint=value.get('endpoint','')
    if not isinstance(endpoint,str) or len(endpoint)>2048: raise ValueError()
    url=urlsplit(endpoint)
    if url.scheme!='https' or url.hostname not in {'fcm.googleapis.com','web.push.apple.com','updates.push.services.mozilla.com'} or url.port not in (None,443) or url.username or url.password or url.fragment or not url.path.strip('/'): raise ValueError()
    keys=value.get('keys',{})
    for name,size in [('p256dh',65),('auth',16)]:
        text=keys.get(name,'')
        if not isinstance(text,str) or len(text)>100: raise ValueError()
        raw=base64.b64decode(text+'='*((-len(text))%4),altchars=b'-_',validate=True)
        if len(raw)!=size: raise ValueError()
        if name=='p256dh':
            from cryptography.hazmat.primitives.asymmetric import ec
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),raw)
    return {'endpoint':endpoint,'keys':{n:keys[n] for n in ('p256dh','auth')}}

def send(session,sub):
    with _lock:
        if _states.get(session)!='pending':return
    try:
        from pywebpush import webpush
        import requests
        class NoRedirect(requests.Session):
            def request(self,*args,**kwargs):
                kwargs['allow_redirects']=False
                return super().request(*args,**kwargs)
        result=webpush(subscription_info=sub,data=json.dumps({'title':'Match Europe — notification de test','body':'Le test fonctionne. Cliquez pour revenir dans Match Europe.'}),vapid_private_key=str(key()[0]),vapid_claims={'sub':'https://matcheurope.beta.francetravail.fr'},ttl=60,timeout=10,requests_session=NoRedirect())
        status='sent' if result.status_code in (200,201,202) else 'failed'
    except Exception:
        status='failed'
    with _lock:_states[session]=status

@local_only
@ensure_csrf_cookie
def api(request,action):
    if not request.session.session_key:request.session.create()
    sid=request.session.session_key
    if request.method=='GET' and action=='config':
        return JsonResponse({'publicKey':key()[1]})
    if request.method=='GET' and action=='status':
        with _lock:state=_states.get(sid,'idle')
        return JsonResponse({'state':state})
    if request.method!='POST':return JsonResponse({'error':'method'},status=405)
    try:
        if len(request.body)>6000:raise ValueError()
        data=json.loads(request.body)
        if action=='subscribe':
            request.session['push_test_subscription']=subscription(data)
            return JsonResponse({'saved':True})
        if action=='stop':
            request.session.pop('push_test_subscription',None)
            with _lock:_states[sid]='cancelled'
            return JsonResponse({'stopped':True})
        if action=='send':
            sub=request.session.get('push_test_subscription')
            if not sub:return JsonResponse({'error':'subscription_required'},status=400)
            with _lock:
                if _states.get(sid)=='pending':return JsonResponse({'error':'pending'},status=409)
                _states[sid]='pending'
            timer=threading.Timer(10,send,args=(sid,sub));timer.daemon=True;timer.start()
            return JsonResponse({'scheduled':True,'delay':10})
    except (ValueError,TypeError,KeyError):return JsonResponse({'error':'invalid'},status=400)
    return JsonResponse({'error':'unknown'},status=404)

@local_only
def worker(request):
    js="""self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
async function report(data){const cache=await caches.open('me-push-test-diagnostics');await cache.put('push-report',new Response(JSON.stringify({...data,at:Date.now()}),{headers:{'Content-Type':'application/json'}}));}
self.addEventListener('push',event=>event.waitUntil((async()=>{await report({stage:'received'});let data={};try{data=event.data.json()}catch{}try{await self.registration.showNotification(data.title||'Match Europe',{body:data.body||'Notification de test',tag:'me-local-test-'+Date.now(),renotify:true,data:{url:'/previews/employer-landing/push-test.html'}});await report({stage:'displayed'});}catch(error){await report({stage:'error',message:error.name+': '+error.message});}})()));
self.addEventListener('notificationclick',event=>{event.notification.close();event.waitUntil(clients.openWindow('/previews/employer-landing/push-test.html'))});"""
    return HttpResponse(js,content_type='application/javascript')
