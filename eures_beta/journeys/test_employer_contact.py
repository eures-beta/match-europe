import json
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import EmployerImport, Profile


@patch.dict('os.environ', {'ME_EMPLOYER_LOCAL_API': '1'})
class EmployerContactTests(TestCase):
    def setUp(self):
        env=patch.dict('os.environ',{'ME_EMPLOYER_LOCAL_API':'1'})
        env.start();self.addCleanup(env.stop)
        self.staff={}
        for role in ('adviser','other','admin','candidate','employer','unverified'):
            user=User.objects.create_user(username=role+'@example.invalid')
            Profile.objects.create(user=user,role='adviser' if role in ('other','unverified') else role,
                                   verified=role!='unverified',name='Fictional '+role)
            self.staff[role]=user
        self.contact={'name':'Fictional Contact','email':'private-contact@example.invalid','phone':'+33 1 00 00 00 00','function':'Fictional recruiter'}
        self.owner=Client()
        response=self.owner.post('/local-api/imports/',{'kind':'manual','text':'Fictional offer description.',
            'email':'workspace@example.invalid','agreement':'true','contact':json.dumps(self.contact)})
        self.assertEqual(response.status_code,201)
        self.obj=EmployerImport.objects.get(pk=response.json()['id'])
        self.obj.adviser=self.staff['adviser'];self.obj.save()
        self.url=reverse('imported_offer',args=[self.obj.pk])

    def login(self,role):
        client=Client();client.force_login(self.staff[role]);return client

    def test_contact_separate_from_offer_and_access_email(self):
        self.assertEqual(self.obj.email,'workspace@example.invalid')
        self.assertEqual(self.obj.contact,self.contact)
        self.assertNotIn('contact',self.obj.data)
        self.assertEqual(self.owner.get(f'/local-api/imports/{self.obj.pk}/').json()['contact'],self.contact)

    def test_contact_required_and_validated_server_side(self):
        for contact in ({},{'name':'Fictional'},dict(self.contact,email='invalid'),dict(self.contact,phone='1'*41),[],'text'):
            with self.subTest(contact=contact):
                response=Client().post('/local-api/imports/',{'kind':'manual','text':'Fictional offer.',
                    'email':'fiction@example.invalid','agreement':'true','contact':json.dumps(contact)})
                self.assertEqual(response.status_code,400)
                self.assertEqual(response.json()['error'],'invalid_contact')

    def test_staff_contact_permissions_and_dashboard_filter(self):
        for role,allowed in [('adviser',True),('admin',True),('other',False),('candidate',False),('employer',False),('unverified',False)]:
            with self.subTest(role=role):
                client=self.login(role)
                response=client.get(self.url)
                self.assertEqual(response.status_code,200 if allowed else 404)
                self.assertEqual(self.contact['email'] in response.content.decode(),allowed)
                dashboard=client.get(reverse('dashboard'))
                self.assertEqual(self.url in dashboard.content.decode(),allowed)
                self.assertEqual(client.get(f'/local-api/imports/{self.obj.pk}/').status_code,404)
        self.assertEqual(Client().get(self.url).status_code,302)

    def test_unassigned_import_only_visible_to_admin(self):
        self.obj.adviser=None;self.obj.save()
        self.assertEqual(self.login('adviser').get(self.url).status_code,404)
        self.assertContains(self.login('admin').get(self.url),self.contact['email'])

    def test_admin_assignment_changes_adviser_access(self):
        admin=self.login('admin')
        response=admin.post(self.url,{'adviser':self.staff['other'].pk})
        self.assertEqual(response.status_code,302)
        self.obj.refresh_from_db();self.assertEqual(self.obj.adviser,self.staff['other'])
        self.assertEqual(self.login('adviser').get(self.url).status_code,404)
        self.assertContains(self.login('other').get(self.url),self.contact['email'])
        self.assertEqual(admin.post(self.url,{'adviser':''}).status_code,302)
        self.assertEqual(self.login('other').get(self.url).status_code,404)

    def test_non_admin_cannot_assign_and_invalid_roles_rejected(self):
        self.assertEqual(self.login('adviser').post(self.url,{'adviser':self.staff['other'].pk}).status_code,404)
        for role in ('candidate','admin','unverified'):
            response=self.login('admin').post(self.url,{'adviser':self.staff[role].pk})
            self.assertEqual(response.status_code,200)
            self.obj.refresh_from_db();self.assertEqual(self.obj.adviser,self.staff['adviser'])

    def test_owner_can_edit_contact_without_external_call_or_offer_invalidation(self):
        self.obj.initial_sent_at=self.obj.validated_at=self.obj.synced_at=timezone.now();self.obj.save()
        payload={'action':'contact','revision':self.obj.revision,'contact':dict(self.contact,name='Changed fictional contact')}
        url=f'/local-api/imports/{self.obj.pk}/'
        with patch('journeys.employer_api.aglae') as api:
            response=self.owner.post(url,json.dumps(payload),content_type='application/json')
            self.assertEqual(response.status_code,200);api.assert_not_called()
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.contact['name'],'Changed fictional contact')
        self.assertIsNotNone(self.obj.validated_at)
        self.assertEqual(self.owner.post(url,json.dumps(payload),content_type='application/json').status_code,409)
        other=Client()
        self.assertEqual(other.post(url,json.dumps(dict(payload,revision=self.obj.revision)),content_type='application/json').status_code,404)

    @patch('journeys.employer_api.aglae')
    def test_contact_not_sent_to_aglae_initial_or_final(self,api):
        from .offer_ingestion import empty_data
        from .employer_api import initial_send
        data=empty_data();data.update(title='Fictional job',companyName='Fictional company',city='Testville',
            description='Fictional description.',contractType='PERMANENT_CONTRACT',geo={'query':'Testville','latitude':48,'longitude':2})
        self.obj.data=data;self.obj.save()
        api.return_value={'id':str(self.obj.pk),'active':False}
        initial_send(self.obj)
        response=self.owner.post(f'/local-api/imports/{self.obj.pk}/',json.dumps({'action':'validate','revision':self.obj.revision,'data':data,'confirmed':True}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        serialized=repr(api.call_args_list)
        for value in self.contact.values(): self.assertNotIn(value,serialized)
        self.assertNotIn('workspace@example.invalid',serialized)

    def test_csrf_and_html_escaping(self):
        self.obj.contact=dict(self.contact,name='<script>alert(1)</script>');self.obj.save()
        self.assertContains(self.login('admin').get(self.url),'&lt;script&gt;alert(1)&lt;/script&gt;')
        client=Client(enforce_csrf_checks=True);client.force_login(self.staff['admin'])
        self.assertEqual(client.post(self.url,{'adviser':''}).status_code,403)
        self.assertEqual(client.get(self.url)['Cache-Control'],'max-age=0, no-cache, no-store, must-revalidate, private')

    def test_legacy_draft_can_add_contact_without_reimport(self):
        self.obj.contact={};self.obj.save()
        url=f'/local-api/imports/{self.obj.pk}/'
        self.assertEqual(self.owner.get(url).json()['contact'],{'email':self.obj.email})
        response=self.owner.post(url,json.dumps({'action':'contact','revision':self.obj.revision,'contact':self.contact}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.obj.refresh_from_db();self.assertEqual(self.obj.contact,self.contact)

    def test_import_cannot_assign_itself_to_an_adviser(self):
        response=self.owner.post('/local-api/imports/',{'kind':'manual','text':'Another fictional draft.',
            'email':'workspace@example.invalid','agreement':'true','contact':json.dumps(self.contact),'adviser':self.staff['adviser'].pk})
        self.assertEqual(response.status_code,201)
        self.assertIsNone(EmployerImport.objects.get(pk=response.json()['id']).adviser)

    def test_staff_page_translations(self):
        for language,heading in [('fr','Contact entreprise'),('de','Unternehmenskontakt'),('en','Company contact')]:
            self.assertContains(self.login('admin').get(self.url,HTTP_ACCEPT_LANGUAGE=language),heading)
