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


def plain(value):
    if not isinstance(value, str): return ''
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', value))).strip()


def empty_data():
    return dict(title='',companyName='',city='',contractType='',description='',desiredProfile='',
                clarifications={k:'' for k in ('salary','hours','startDate','frenchLevel','experience','commute')},
                crossBorder='',relocation='',questions=[],requirements=dict(workConditions=[],permitRequired='',permits=[],permitOther='',arrivalAids=[],aidOther=''))


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


