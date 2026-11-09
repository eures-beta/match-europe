from datetime import timedelta
from django.apps import apps
from django.contrib import admin
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from io import StringIO

from eures_beta.users.models import User, EmployerInvitation, LoginRateLimit
from eures_beta.users.admin_base import MetadataOnlyAdmin
from eures_beta.employers.models import (
    EmployerProfile,
    Company,
    CompanyMembership,
    JobOffer,
    EmployerEmailLink,
    EmployerSearchOperation,
    EmployerSearchEvent,
)


class ReadOnlyAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            'operator@example.invalid', kind='adviser'
        )
        self.staff = User.objects.create_user(
            'staff@example.invalid', kind='adviser', is_staff=True
        )
        self.employer = User.objects.create_user(
            'employer@example.invalid', kind='employer'
        )
        self.company = Company.objects.create(name='Fictional company')
        self.membership = CompanyMembership.objects.create(
            company=self.company, person=self.employer
        )
        self.offer = JobOffer.objects.create(
            company=self.company,
            created_by=self.employer,
            session_key='never-show-session-key',
            email=self.employer.email,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            source_url='https://example.invalid/offer?token=url-secret&reference=public',
            data={
                'title': 'Fictional offer',
                'nested': [{'api_key': 'nested-secret'}],
                'html': '<script>alert(1)</script>',
            },
            contact={'email': self.employer.email, 'password': 'contact-secret'},
            sandbox_response={'authorization': 'external-secret', 'status': 'ok'},
        )
        self.link = EmployerEmailLink.objects.create(
            email=self.employer.email,
            pending_import=self.offer,
            digest='never-show-digest',
            expires=timezone.now() + timedelta(hours=1),
        )
        self.operation = EmployerSearchOperation.objects.create(
            offer=self.offer,
            requested_by=self.employer,
            revision=1,
            state='started',
            scenario='fictional',
        )
        self.event = EmployerSearchEvent.objects.create(
            operation=self.operation, actor=self.employer, state='started'
        )
        self.invitation = EmployerInvitation.objects.create(
            email='invited@example.invalid', invited_by=self.superuser
        )
        self.limit = LoginRateLimit.objects.create(
            key='fictional-rate-bucket', expires=timezone.now() + timedelta(hours=1)
        )
        self.session_record = Session.objects.create(
            session_key='never-show-other-session-key',
            session_data='never-show-session-data',
            expire_date=timezone.now() + timedelta(days=1),
        )
        self.log = LogEntry.objects.create(
            user=self.superuser,
            content_type=ContentType.objects.get_for_model(User),
            object_id=str(self.employer.pk),
            object_repr='Fictional employer',
            action_flag=ADDITION,
            change_message='never-show-log-payload',
        )
        call_command('sync_group_and_perms', stdout=StringIO())
        self.response_practice = EmployerProfile.objects.create(
            user=self.employer,
            response_coverage='all',
            response_time='under_week',
        )
        self.records = [
            self.response_practice,
            self.company,
            self.membership,
            self.offer,
            self.link,
            self.operation,
            self.event,
            self.invitation,
            self.limit,
            self.employer,
            Group.objects.first(),
            Permission.objects.first(),
            ContentType.objects.first(),
            self.session_record,
            self.log,
        ]
        self.client.force_login(self.superuser)

    def url(self, record, operation):
        meta = record._meta
        return reverse(
            f'admin:{meta.app_label}_{meta.model_name}_{operation}',
            args=[] if operation in ('changelist', 'add') else [record.pk],
        )

    def test_every_installed_model_is_explicitly_registered(self):
        self.assertEqual(set(apps.get_models()), set(admin.site._registry))

    def test_superuser_can_list_all_models_and_read_business_objects(self):
        for record in self.records:
            with self.subTest(model=record._meta.label):
                self.assertEqual(
                    self.client.get(self.url(record, 'changelist')).status_code, 200
                )
                if not isinstance(
                    admin.site._registry[type(record)], MetadataOnlyAdmin
                ):
                    page = self.client.get(self.url(record, 'change'))
                    self.assertEqual(page.status_code, 200)
                    self.assertNotContains(page, 'name="_save"')
                    self.assertNotContains(page, 'class="deletelink"')
        self.assertContains(
            self.client.get(self.url(self.offer, 'change')), 'Fictional offer'
        )

    def test_all_write_routes_are_denied_even_to_superuser(self):
        for record in self.records:
            with self.subTest(model=record._meta.label):
                model = type(record)
                count = model.objects.count()
                original = model.objects.filter(pk=record.pk).values().get()
                for operation in ('add', 'change', 'delete'):
                    self.assertEqual(
                        self.client.post(
                            self.url(record, operation),
                            {'name': 'Changed', 'post': 'yes'},
                        ).status_code,
                        403,
                    )
                page = self.client.post(
                    self.url(record, 'changelist'),
                    {
                        'action': 'delete_selected',
                        '_selected_action': str(record.pk),
                        'post': 'yes',
                    },
                )
                self.assertIn(page.status_code, (200, 302))
                self.assertEqual(model.objects.count(), count)
                self.assertEqual(
                    self.client.get(self.url(record, 'history')).status_code, 403
                )
                self.assertEqual(
                    model.objects.filter(pk=record.pk).values().get(), original
                )
                self.assertFalse(
                    admin.site._registry[model].get_actions(page.wsgi_request)
                )

    def test_other_accounts_cannot_read_business_or_framework_models_even_with_permissions(
        self,
    ):
        self.staff.user_permissions.set(Permission.objects.all())
        self.client.force_login(self.staff)
        for record in self.records:
            if isinstance(record, User):
                continue
            with self.subTest(model=record._meta.label):
                self.assertEqual(
                    self.client.get(self.url(record, 'changelist')).status_code, 403
                )
                self.assertEqual(
                    self.client.get(self.url(record, 'change')).status_code, 403
                )
        self.assertNotContains(
            self.client.get(reverse('admin:index')), 'Fictional company'
        )
        self.client.force_login(self.employer)
        self.assertEqual(
            self.client.get(self.url(self.offer, 'changelist')).status_code, 302
        )
        self.client.logout()
        self.assertEqual(
            self.client.get(self.url(self.offer, 'changelist')).status_code, 302
        )

    def test_inactive_superuser_and_superuser_without_staff_cannot_enter(self):
        for field in ('is_active', 'is_staff'):
            with self.subTest(field=field):
                setattr(self.superuser, field, False)
                self.superuser.save(update_fields=[field])
                self.client.force_login(self.superuser)
                self.assertEqual(
                    self.client.get(reverse('admin:index')).status_code, 302
                )
                setattr(self.superuser, field, True)
                self.superuser.save(update_fields=[field])

    def test_known_secrets_are_hidden_and_json_is_escaped(self):
        page = self.client.get(self.url(self.offer, 'change'))
        for secret in (
            'never-show-session-key',
            'nested-secret',
            'contact-secret',
            'external-secret',
            'url-secret',
        ):
            self.assertNotContains(page, secret)
        self.assertNotContains(page, '<script>alert(1)</script>')
        self.assertContains(page, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertContains(page, self.employer.email)
        self.assertContains(page, 'reference=public')
        self.assertNotContains(
            self.client.get(self.url(self.link, 'change')), self.link.digest
        )
        self.assertNotContains(
            self.client.get(self.url(self.invitation, 'change')),
            str(self.invitation.nonce),
        )
        self.employer.set_password('fictional-password')
        self.employer.save()
        self.assertNotContains(
            self.client.get(self.url(self.employer, 'change')), self.employer.password
        )

    def test_sessions_and_log_entries_expose_only_safe_list_metadata(self):
        self.log.object_repr = 'sensitive-history-label'
        self.log.save(update_fields=['object_repr'])
        index = self.client.get(reverse('admin:index'))
        self.assertNotContains(index, 'sensitive-history-label')
        for record, secret in (
            (self.session_record, self.session_record.session_key),
            (self.log, 'never-show-log-payload'),
        ):
            page = self.client.get(self.url(record, 'changelist'))
            self.assertNotContains(page, secret)
            self.assertNotContains(page, self.session_record.session_data)
            self.assertEqual(
                self.client.get(self.url(record, 'change')).status_code, 403
            )
            self.assertEqual(
                self.client.get(self.url(record, 'history')).status_code, 403
            )
        popup = self.client.get(
            self.url(self.session_record, 'changelist'), {'_popup': '1'}
        )
        self.assertNotContains(popup, self.session_record.session_key)

    def test_search_and_filters_keep_the_read_only_behavior(self):
        page = self.client.get(self.url(self.company, 'changelist'), {'q': 'Fictional'})
        self.assertContains(page, self.company.name)
        page = self.client.get(
            self.url(self.offer, 'changelist'), {'source_kind': 'manual'}
        )
        self.assertContains(page, str(self.offer.pk))
