"""Bounded public-page/PDF reading. No AI inference, no third-party credential forwarding."""
import http.client
import ipaddress
import json
import re
import socket
import ssl
import subprocess
import sys
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin


class ImportFailure(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def public_target(url):
    try:
        p = urlsplit(url)
        if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
            raise ValueError()
        host = p.hostname.encode('idna').decode('ascii').rstrip('.')
        if len(url) > 2048 or any(c in url for c in '\r\n\\') or '.' not in host:
            raise ValueError()
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(a).is_global or ipaddress.ip_address(a).is_multicast for a in addresses):
            raise ValueError()
        return p, host, sorted(addresses)[0]
    except (ValueError, UnicodeError, OSError):
        raise ImportFailure('unsafe_url') from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=10, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def fetch_public(url, allowed_types=('text/html', 'application/xhtml+xml')):
    """Pin each validated DNS answer to the TLS socket, including on redirects."""
    deadline = time.monotonic() + 25
    for _ in range(4):
        p, host, address = public_target(url)
        conn = PinnedHTTPS(host, address)
        try:
            conn.request('GET', (p.path or '/') + ('?' + p.query if p.query else ''), headers={
                'User-Agent': 'MatchEurope-LocalSandbox/1.0', 'Accept': ','.join(allowed_types), 'Accept-Encoding': 'identity'})
            r = conn.getresponse()
            if r.status in (301, 302, 303, 307, 308):
                location = r.getheader('Location')
                if not location: raise ImportFailure('unreadable_url')
                url = urljoin(url, location)
                continue
            if r.status != 200: raise ImportFailure('unreadable_url')
            if r.getheader('Content-Type', '').split(';')[0] not in allowed_types:
                raise ImportFailure('unreadable_url')
            if r.getheader('Content-Encoding', 'identity') not in ('identity', ''):
                raise ImportFailure('unreadable_url')
            chunks = []; size = 0
            while True:
                if time.monotonic() > deadline: raise ImportFailure('unreadable_url')
                chunk = r.read(32768)
                if not chunk: break
                size += len(chunk)
                if size > 2 * 1024 * 1024: raise ImportFailure('unreadable_url')
                chunks.append(chunk)
            return b''.join(chunks).decode('utf-8', errors='replace'), url
        except (OSError, http.client.HTTPException):
            raise ImportFailure('unreadable_url') from None
        finally:
            conn.close()
    raise ImportFailure('unreadable_url')


def read_url(url):
    p=urlsplit(url)
    match=re.fullmatch(r'/offres/recherche/detail/([A-Za-z0-9]{7,20})/?',p.path)
    if p.hostname=='candidat.francetravail.fr' and not match:
        raise ImportFailure('individual_offer_required')
    if p.hostname=='candidat.francetravail.fr' and match:
        # This is the unauthenticated public resource used by the site's descriptif-offre component.
        # Never use the publisher's address as the workplace address.
        public_target(url)
        raw,_=fetch_public('https://candidat.francetravail.fr/api-descriptifoffre/offre/'+match.group(1),('application/json',))
        try: item=json.loads(raw)
        except ValueError: raise ImportFailure('unreadable_url') from None
        if not isinstance(item,dict) or str(item.get('numeroOffre','')).removeprefix('Offre n° ').strip()!=match.group(1): raise ImportFailure('unreadable_url')
        data=empty_data();data['extraction']='france_travail_public'
        data['title']=plain(item.get('intituleOffre'))[:125]
        data['city']=(plain(item.get('lieuTravail'))+', France')[:150]
        publisher=item.get('etablissement') or {}
        data['companyName']=plain(publisher.get('libelleEnseigne'))[:100] if isinstance(publisher,dict) else ''
        data['description']=plain(item.get('descriptif'))[:16000]
        contract=plain(item.get('syntheseContrat'))
        if re.search(r'\bCDI\b',contract): data['contractType']='PERMANENT_CONTRACT'
        elif re.search(r'\bCDD\b',contract): data['contractType']='FIXED_TERM_CONTRACT'
        skills=item.get('listeCompetence') or []
        data['desiredProfile']='\n'.join(plain(x.get('libelleCompetence')) for x in skills if isinstance(x,dict))[:4000]
        data['clarifications']['salary']=plain(item.get('salaire'))[:1000]
        conditions=item.get('conditionTravailPoste') or {}
        hour_parts=[]
        hours=plain(item.get('syntheseHoraire'))
        if hours and hours.lower() not in ('non disponible','non précisé'): hour_parts.append(hours)
        if isinstance(conditions,dict):
            for key in ('listeLibelleTypeHoraire','listeLibelleConditionExerciceHoraire'):
                entries=conditions.get(key) or []
                if isinstance(entries,list):
                    hour_parts.extend(plain(value) for value in entries if isinstance(value,str) and plain(value))
            # These are workplace conditions, never the recruiting agency's opening hours.
            for key in ('libelleConditionTravail','commentaireConditionTravail'):
                value=conditions.get(key)
                if isinstance(value,str) and plain(value): hour_parts.append(plain(value))
        data['clarifications']['hours']=' ; '.join(dict.fromkeys(hour_parts))[:1000]
        # Only explicit working-hour conditions; never infer from the agency description.
        hours_text=data['clarifications']['hours'].lower()
        for code,pattern in [('weekend',r'samedi|dimanche|week.end|jours fériés'),('night',r'nuit|soirée'),('shift',r'travail posté'),('variable',r'horaires variables')]:
            if re.search(pattern,hours_text): data['requirements']['workConditions'].append(code)
        experience=item.get('experienceProfil') or {}
        if isinstance(experience,dict): data['clarifications']['experience']=plain(experience.get('experience'))[:1000]
        data['clarifications']['frenchLevel']='; '.join(plain(x.get('libelleLangue')) for x in item.get('listeLangue',[]) if isinstance(x,dict))[:1000]
        if not data['description'] or not data['title']: raise ImportFailure('unreadable_url')
        return data,url
    html,final=fetch_public(url)
    # Dynamic FT pages must never silently fall back to neighbouring job recommendations.
    if '<descriptif-offre' in html: raise ImportFailure('unreadable_url')
    return parse_page(html),final


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ld = []; self.script = None; self.script_text = []; self.skip = 0
        self.text = []; self.title = []; self.in_title = False; self.meta_title = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script': self.script = a.get('type', ''); self.script_text = []
        if tag in ('style','nav','footer','header','noscript'): self.skip += 1
        if tag == 'title': self.in_title = True
        if tag == 'meta' and a.get('property') == 'og:title': self.meta_title = a.get('content', '')
        if tag in ('p','div','li','br','h1','h2','h3'): self.text.append('\n')
    def handle_endtag(self, tag):
        if tag == 'script':
            if self.script == 'application/ld+json':
                try: self.ld.append(json.loads(''.join(self.script_text)))
                except (ValueError, RecursionError): pass
            self.script = None
        if tag in ('style','nav','footer','header','noscript'): self.skip = max(0,self.skip-1)
        if tag == 'title': self.in_title = False
    def handle_data(self, data):
        if self.script is not None: self.script_text.append(data)
        elif not self.skip:
            if self.in_title: self.title.append(data)
            else: self.text.append(data)


def plain(value):
    if not isinstance(value, str): return ''
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', value))).strip()


def find_job(value, depth=0):
    if depth > 12: return None
    if isinstance(value, list):
        for x in value:
            found = find_job(x, depth+1)
            if found: return found
    if isinstance(value, dict):
        kind = value.get('@type', [])
        if kind == 'JobPosting' or isinstance(kind,list) and 'JobPosting' in kind: return value
        for x in value.values():
            if isinstance(x,(dict,list)):
                found = find_job(x, depth+1)
                if found: return found
    return None


def empty_data():
    return dict(title='',companyName='',city='',contractType='',description='',desiredProfile='',
                clarifications={k:'' for k in ('salary','hours','startDate','frenchLevel','experience','commute')},
                crossBorder='',relocation='',questions=[],requirements=dict(workConditions=[],permitRequired='',permits=[],permitOther='',arrivalAids=[],aidOther=''))


def parse_page(html):
    page = Page()
    try: page.feed(html)
    except (ValueError,RecursionError): raise ImportFailure('unreadable_url') from None
    job = find_job(page.ld)
    data = empty_data()
    if not job:
        data['title'] = plain(page.meta_title or ''.join(page.title))[:125]
        data['description'] = re.sub(r'\n\s*\n+', '\n', ''.join(page.text)).strip()[:16000]
        if len(data['description']) < 50: raise ImportFailure('unreadable_url')
        data['extraction'] = 'page_text'
        return data
    data['extraction'] = 'jobposting_jsonld'
    data['title'] = plain(job.get('title'))[:125]
    org = job.get('hiringOrganization', {})
    if isinstance(org,dict): data['companyName'] = plain(org.get('name'))[:100]
    data['description'] = plain(job.get('description'))[:16000]
    data['desiredProfile'] = plain(job.get('qualifications') or job.get('skills'))[:4000]
    location = job.get('jobLocation', {})
    if isinstance(location,list): location = location[0] if location else {}
    address = location.get('address', {}) if isinstance(location,dict) else {}
    if isinstance(address,dict):
        country = address.get('addressCountry', '')
        if isinstance(country,dict): country=country.get('name','')
        data['city'] = ', '.join(str(address[k]) for k in ('streetAddress','postalCode','addressLocality') if address.get(k))[:150]
        data['country'] = plain(country)
        if data['country'] and data['city']:
            data['city']=(data['city']+', '+data['country'])[:150]
    kind=job.get('employmentType','')
    if isinstance(kind,list): kind=kind[0] if kind else ''
    if not isinstance(kind,str): kind=''
    data['contractType'] = {'FULL_TIME':'', 'PART_TIME':'', 'PERMANENT':'PERMANENT_CONTRACT','CONTRACTOR':'FREELANCE', 'TEMPORARY':'TEMPORARY_WORK','INTERN':'INTERNSHIP'}.get(kind, '')
    # Only explicit contract wording. FULL_TIME is not a permanent contract.
    if re.search(r'\bCDI\b',data['description']): data['contractType']='PERMANENT_CONTRACT'
    elif re.search(r'\bCDD\b',data['description']): data['contractType']='FIXED_TERM_CONTRACT'
    if kind in ('FULL_TIME','PART_TIME'): data['clarifications']['hours'] = kind
    data['clarifications']['startDate']=plain(job.get('jobStartDate'))[:150]
    salary=job.get('baseSalary')
    if isinstance(salary,dict):
        value=salary.get('value',{})
        if isinstance(value,dict):
            parts=[value.get('value'),value.get('minValue'),value.get('maxValue'),salary.get('currency'),value.get('unitText')]
            data['clarifications']['salary']=' '.join(str(x) for x in parts if x is not None)[:150]
    return data


def read_pdf(upload):
    if upload.size > 10*1024*1024: raise ImportFailure('large')
    if not upload.name.lower().endswith('.pdf') or upload.read(5)!=b'%PDF-': raise ImportFailure('invalid')
    upload.seek(0)
    try:
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('pdf_reader.py'))],input=upload.read(),capture_output=True,timeout=15,check=True)
        text=json.loads(result.stdout)['text']
    except Exception: raise ImportFailure('unreadable') from None
    if not text.strip(): raise ImportFailure('unreadable')
    return parse_pdf_text(text)


def parse_pdf_text(text):
    # Some embedded fonts map Latin a to IPA alpha. Keep all other characters.
    text=text.replace('ɑ','a')
    lines=[line.strip().strip('•●▪◦ ').strip() for line in text.splitlines()]
    lines=[line for line in lines if line and any(c.isalnum() for c in line)]
    data=empty_data();data['description']=text[:16000];data['extraction']='pdf_text'
    data['title']=next((line for line in lines if not re.fullmatch(r'\d+',line)),'')[:125]
    # Recognise a compact offer header: title, employer, postal workplace.
    # Do not scan the body for arbitrary addresses or infer a missing employer.
    if len(lines)>=3 and re.fullmatch(r"\d{5}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \-’']+",lines[2]) and len(lines[1])<=125:
        data['companyName']=lines[1]
        data['city']=lines[2]
    labels={
        'title':r'(?:intitulé du poste|poste|job title|stellenbezeichnung)',
        'companyName':r'(?:entreprise|employeur|company|employer|unternehmen|arbeitgeber)',
        'city':r'(?:lieu de travail|lieu|workplace|location|arbeitsort)',
    }
    for field,label in labels.items():
        values=[m.group(1).strip() for line in lines[:20] if (m:=re.fullmatch(label+r'\s*:\s*(.+)',line,re.I))]
        if len(set(values))==1:
            data[field]=values[0][:125] if field!='city' else values[0]
    # A unique explicit contract marker can be copied; conflicting markers stay blank.
    markers={'PERMANENT_CONTRACT':r'\bCDI\b','FIXED_TERM_CONTRACT':r'\bCDD\b'}
    found=[kind for kind,pattern in markers.items() if re.search(pattern,'\n'.join(lines[:15]),re.I)]
    if len(found)==1: data['contractType']=found[0]
    return data
