import json
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .models import EmployerImport
from .offer_ingestion import parse_page, public_target, ImportFailure, read_url


class ReadingTests(SimpleTestCase):


    def test_requirements_validation_and_backward_compatible_defaults(self):
        from .employer_api import clean_data
        data=clean_data({'requirements':{'workConditions':['weekend','physical'],'permitRequired':'yes','permits':['B','other'],'permitOther':'Autorisation fictive','arrivalAids':['housing']}})
        self.assertEqual(data['requirements']['permits'],['B','other'])
        self.assertEqual(data['requirements']['arrivalAids'],['housing'])
        self.assertEqual(clean_data({})['requirements']['workConditions'],[])
        for req in ({'workConditions':['none','night']},{'permits':['invalid']},{'arrivalAids':'housing'},{'permitRequired':'invalid'}):
            with self.assertRaises(ImportFailure): clean_data({'requirements':req})
        cleared=clean_data({'requirements':{'permitRequired':'no','permits':['B'],'permitOther':'Hidden value'}})
        self.assertEqual(cleared['requirements']['permits'],[])
        self.assertEqual(cleared['requirements']['permitOther'],'')









@patch.dict('os.environ',{'ME_EMPLOYER_LOCAL_API':'1'})
class ImportFlowTests(TestCase):
    def create(self):
        return self.client.post('/local-api/imports/',{'kind':'manual','text':'A useful fictional job description.','contact':json.dumps({'name':'Fictional contact','email':'contact@example.invalid'}),'email':'fiction@example.invalid','agreement':'true'})

    def payload(self,result):
        data=result['data']
        data.update(title='Example role',companyName='Example company',city='Testville',contractType='PERMANENT_CONTRACT')
        return data

    def update(self,result,action='save',**kwargs):
        return self.client.post('/local-api/imports/'+result['id']+'/',json.dumps({'action':action,'revision':result['revision'],'data':self.payload(result),**kwargs}),content_type='application/json')

    def test_draft_stored_and_owned_by_session(self):
        response=self.create();self.assertEqual(response.status_code,201)
        obj=response.json();self.assertTrue(EmployerImport.objects.filter(pk=obj['id']).exists())
        self.assertEqual(self.client.get('/local-api/imports/'+obj['id']+'/').status_code,200)
        self.assertEqual(Client().get('/local-api/imports/'+obj['id']+'/').status_code,404)

    def test_requirements_survive_save_and_resume(self):
        created=self.create().json()
        req={'workConditions':['weekend','standing'],'permitRequired':'yes','permits':['B'],
             'permitOther':'','arrivalAids':['housing','admin'],'aidOther':''}
        created['data']['requirements']=req
        response=self.update(created)
        self.assertEqual(response.status_code,200)
        resumed=self.client.get('/local-api/imports/'+created['id']+'/').json()
        self.assertEqual(resumed['data']['requirements'],req)
        self.assertEqual(EmployerImport.objects.get(pk=created['id']).data['requirements'],req)

    def test_consent_required_before_reading(self):
        with patch('journeys.offer_ingestion.fetch_public') as fetch:
            r=self.client.post('/local-api/imports/',{'kind':'url','url':'https://example.org/job','contact':json.dumps({'name':'Fictional contact','email':'contact@example.invalid'}),'email':'fiction@example.invalid'})
            self.assertEqual(r.status_code,400);fetch.assert_not_called()

    def test_real_parser_not_saved_example(self):
        html='<script type="application/ld+json">'+json.dumps({'@type':'JobPosting','title':'Different job','description':'Different fictional job description','hiringOrganization':{'name':'Different company'}})+'</script>'
        with patch('journeys.offer_ingestion.fetch_public',return_value=(html,'https://example.org/different')):
            first=self.client.post('/local-api/imports/source/',{'url':'https://example.org/different','agreement':'true'})
            self.assertEqual(first.status_code,200)
            r=self.client.post('/local-api/imports/',{'kind':'url','url':'https://example.org/different','contact':json.dumps({'name':'Fictional contact','email':'contact@example.invalid'}),'email':'fiction@example.invalid','agreement':'true','sourceToken':first.json()['token']})
        self.assertEqual(r.status_code,201);self.assertEqual(r.json()['data']['title'],'Different job')

    @patch('journeys.offer_ingestion.fetch_public',side_effect=ImportFailure('unreadable_url'))
    def test_blocked_source_fails_before_email(self,fetch):
        r=self.client.post('/local-api/imports/source/',{'url':'https://example.org/blocked','agreement':'true'})
        self.assertEqual(r.status_code,400)
        self.assertEqual(EmployerImport.objects.count(),0)

    def test_preflight_cannot_be_reused_for_another_source(self):
        session=self.client.session
        session['pending_offer_source']={'url':'https://example.org/one','token':'test','at':9999999999,'data':{}}
        session.save()
        r=self.client.post('/local-api/imports/',{'kind':'url','url':'https://example.org/two','contact':json.dumps({'name':'Fictional contact','email':'contact@example.invalid'}),'email':'fiction@example.invalid','agreement':'true','sourceToken':'test'})
        self.assertEqual(r.status_code,400)

    @patch('journeys.employer_api.read_pdf',return_value={'description':'Fictional PDF text'})
    def test_pdf_read_before_email_and_reused_once(self,read):
        first=self.client.post('/local-api/imports/source/',{'kind':'pdf','agreement':'true','document':SimpleUploadedFile('offer.pdf',b'%PDF-test')})
        self.assertEqual(first.status_code,200)
        self.assertEqual(EmployerImport.objects.count(),0)
        payload={'kind':'pdf','agreement':'true','contact':json.dumps({'name':'Fictional contact','email':'contact@example.invalid'}),'email':'fiction@example.invalid','sourceToken':first.json()['token']}
        self.assertEqual(Client().post('/local-api/imports/',payload).status_code,400)
        created=self.client.post('/local-api/imports/',payload)
        self.assertEqual(created.status_code,201)
        self.assertEqual(created.json()['data']['description'],'Fictional PDF text')
        self.assertEqual(self.client.post('/local-api/imports/',payload).status_code,400)
        read.assert_called_once()

    @patch('journeys.employer_api.read_pdf',side_effect=ImportFailure('unreadable'))
    def test_unreadable_pdf_fails_before_email(self,read):
        payload={'kind':'pdf','document':SimpleUploadedFile('offer.pdf',b'%PDF-test')}
        self.assertEqual(self.client.post('/local-api/imports/source/',payload).status_code,400)
        read.assert_not_called()
        payload.update(agreement='true',document=SimpleUploadedFile('offer.pdf',b'%PDF-test'))
        response=self.client.post('/local-api/imports/source/',payload)
        self.assertEqual(response.json()['error'],'unreadable')
        self.assertEqual(EmployerImport.objects.count(),0)

    @patch('journeys.employer_api.read_pdf',return_value={'description':'Fictional PDF text'})
    def test_expired_pdf_preflight_is_rejected(self,read):
        first=self.client.post('/local-api/imports/source/',{'kind':'pdf','agreement':'true','document':SimpleUploadedFile('offer.pdf',b'%PDF-test')})
        session=self.client.session
        pending=session['pending_offer_source'];pending['at']=0
        session['pending_offer_source']=pending;session.save()
        self.assertEqual(self.client.post('/local-api/imports/',{'kind':'pdf','agreement':'true','contact':json.dumps({'name':'Fictional contact','email':'contact@example.invalid'}),'email':'fiction@example.invalid','sourceToken':first.json()['token']}).status_code,400)

    def test_persistent_edit_and_revision(self):
        obj=self.create().json();r=self.update(obj)
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get('/local-api/imports/'+obj['id']+'/').json()['data']['title'],'Example role')
        self.assertEqual(self.update(obj).status_code,409)

    @patch('journeys.employer_api.aglae')
    def test_no_api_call_without_validation_or_location(self,api):
        obj=self.create().json();self.assertEqual(self.update(obj).status_code,200)
        obj=self.client.get('/local-api/imports/'+obj['id']+'/').json()
        self.assertEqual(self.update(obj,'validate',confirmed=True).status_code,400)
        api.assert_not_called()




    def test_remote_client_and_missing_csrf_rejected(self):
        self.assertEqual(self.client.get('/local-api/imports/',REMOTE_ADDR='192.0.2.1').status_code,404)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/local-api/imports/',{}).status_code,403)

    def test_pdf_reader_receives_actual_document(self):
        with patch('journeys.offer_ingestion.subprocess.run') as run:
            run.return_value.stdout=json.dumps({'text':'Example extracted title\nAn actual extracted fictional document.'}).encode()
            first=self.client.post('/local-api/imports/source/',{'kind':'pdf','document':SimpleUploadedFile('test.pdf',b'%PDF-1.4\nfiction'),'agreement':'true'})
            self.assertEqual(first.status_code,200)
            r=self.client.post('/local-api/imports/',{'kind':'pdf','sourceToken':first.json()['token'],'contact':json.dumps({'name':'Fictional contact','email':'contact@example.invalid'}),'email':'fiction@example.invalid','agreement':'true'})
            self.assertEqual(r.status_code,201);self.assertEqual(r.json()['data']['title'],'Example extracted title')
