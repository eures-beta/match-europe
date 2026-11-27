"""A populated PostgreSQL move preserves the whole dossier and authorization IDs."""

from io import StringIO

from django.apps import apps as current_apps
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase
from django.utils import timezone

from eures_beta.matching.migrations._domain_transfer import DOMAIN_MODELS

BEFORE = ('matching', '0034_merge_employer_review_and_followup')
AFTER = ('matching', '0036_complete_domain_extraction')


class DomainBoundariesTests(SimpleTestCase):
    def test_admin_domain_labels_are_translated(self):
        from django.utils import translation

        for language, expected in {
            'fr': ('Mises en relation', 'Accompagnement et suivi'),
            'de': ('Kontaktanbahnung', 'Begleitung und Nachverfolgung'),
        }.items():
            with translation.override(language):
                actual = tuple(
                    str(current_apps.get_app_config(app).verbose_name)
                    for app in ('introductions', 'followup')
                )
                self.assertEqual(actual, expected)

    def test_three_apps_own_the_existing_sixteen_models(self):
        expected = {
            'matching': {'CandidateOfferMatch', 'MatchEvaluation', 'MatchDecision'},
            **{app: set(names) for app, names in DOMAIN_MODELS.items()},
        }
        for app, names in expected.items():
            with self.subTest(app=app):
                self.assertEqual(
                    {m.__name__ for m in current_apps.get_app_config(app).get_models()},
                    names,
                )

    def test_core_matching_cannot_import_later_process_domains(self):
        import ast
        from django.conf import settings

        for path in (settings.APPS_DIR / 'matching').rglob('*.py'):
            if 'migrations' in path.parts or 'management' in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                names = []
                if isinstance(node, ast.ImportFrom):
                    names.append(node.module or '')
                elif isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                self.assertFalse(
                    any(
                        name.startswith(
                            ('eures_beta.introductions', 'eures_beta.followup')
                        )
                        for name in names
                    ),
                    path,
                )


class DomainExtractionMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        loader = MigrationExecutor(connection).loader
        return loader.project_state(
            [node for node in loader.applied_migrations if node in loader.graph.nodes]
        ).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        ContentType.objects.clear_cache()
        super().tearDown()

    def seed(self, apps):
        get = apps.get_model
        User = get('users', 'User')
        adviser = User.objects.create(email='adviser@domains.invalid', kind='adviser')
        candidate = User.objects.create(
            email='candidate@domains.invalid', kind='candidate'
        )
        employer = User.objects.create(
            email='employer@domains.invalid', kind='employer'
        )
        profile = get('candidates', 'CandidateProfile').objects.create(user=candidate)
        offer = get('employers', 'JobOffer').objects.create(
            employer=employer,
            preparation_agreed_at=timezone.now(),
            source_kind='text',
            data={'title': 'Fictional offer'},
        )
        match = get('matching', 'CandidateOfferMatch').objects.create(
            candidate=profile, offer=offer, candidate_facts={'kept': True}
        )
        review = get('matching', 'CandidateOfferReview').objects.create(
            match=match, requested_by_adviser=adviser, summary={'kept': 'review'}
        )
        get('matching', 'CandidateOfferReviewEvent').objects.create(
            review=review,
            actor=adviser,
            version=1,
            action='claim',
            snapshot={'kept': 1},
        )
        get('matching', 'CandidateOfferReviewAnswer').objects.create(
            review=review,
            question_key='condition',
            fingerprint='a' * 64,
            presented={'text': 'Fictional condition'},
            value='yes',
            dialogue={'kept': True},
        )
        sharing = get('matching', 'CandidateProfileSharing').objects.create(
            review=review, fingerprint='b' * 64, agreed=True
        )
        conversation = get('matching', 'CandidateOfferConversation').objects.create(
            offer_review=review,
            adviser=adviser,
            candidate=candidate,
            employer=employer,
            introduction='Fictional introduction',
        )
        get('matching', 'CandidateOfferConversationMessage').objects.create(
            conversation=conversation, author=candidate, body='Fictional reply'
        )
        get('matching', 'EmployerCandidateReview').objects.create(
            agreement=sharing,
            requested_by_adviser=adviser,
            employer=employer,
            questions=[{'kept': True}],
            replies={'kept': 'reply'},
        )
        get('matching', 'JobOfferSupport').objects.create(
            job_offer=offer, updated_by_adviser=adviser, is_searching=True
        )
        get('matching', 'CandidateSupport').objects.create(
            candidate_profile=profile, updated_by_adviser=adviser, is_searching=True
        )
        plan = get('matching', 'MatchFollowup').objects.create(
            match=match,
            updated_by_adviser=adviser,
            next_action='Fictional next action',
        )
        get('matching', 'MatchFollowupEvent').objects.create(
            followup=plan, actor=adviser, action='plan', snapshot={'kept': 'plan'}
        )
        conclusion = get('matching', 'MatchConclusion').objects.create(
            match=match,
            state='stopped',
            confirmed_by_adviser=adviser,
            confirmed_at=timezone.now(),
            reason='Fictional closure',
        )
        get('matching', 'MatchConclusionEvent').objects.create(
            conclusion=conclusion, actor=adviser, action='stopped', version=1
        )
        return adviser, candidate, review

    def snapshot(self, apps, moved):
        result = {}
        with connection.cursor() as cursor:
            for app, names in DOMAIN_MODELS.items():
                for name in names:
                    model = apps.get_model(app if moved else 'matching', name)
                    table = model._meta.db_table
                    cursor.execute('SELECT %s::regclass::oid', [table])
                    table_oid = cursor.fetchone()[0]
                    cursor.execute(
                        f'SELECT * FROM {connection.ops.quote_name(table)} ORDER BY id'
                    )
                    rows = cursor.fetchall()
                    cursor.execute(
                        'SELECT pg_get_serial_sequence(%s, %s)::regclass::oid',
                        [table, 'id'],
                    )
                    sequence_oid = cursor.fetchone()[0]
                    cursor.execute(
                        'SELECT t.oid, p.oid FROM pg_trigger t '
                        'JOIN pg_proc p ON p.oid=t.tgfoid '
                        'WHERE t.tgrelid=%s::regclass AND NOT t.tgisinternal ORDER BY t.oid',
                        [table],
                    )
                    guards = cursor.fetchall()
                    result[name] = (table_oid, rows, sequence_oid, guards)
        return result

    def grants(self, apps, adviser):
        get = apps.get_model
        adviser = get('users', 'User').objects.get(pk=adviser.pk)
        group = get('auth', 'Group').objects.create(name='domain-extraction-grants')
        saved = []
        for names in DOMAIN_MODELS.values():
            for name in names:
                ct, _ = get('contenttypes', 'ContentType').objects.get_or_create(
                    app_label='matching', model=name.lower()
                )
                permission, _ = get('auth', 'Permission').objects.get_or_create(
                    content_type=ct,
                    codename='view_' + name.lower(),
                    defaults={'name': 'Can view ' + name},
                )
                group.permissions.add(permission)
                adviser.user_permissions.add(permission)
                log = get('admin', 'LogEntry').objects.create(
                    user=adviser,
                    content_type=ct,
                    object_id='1',
                    object_repr='Fictional object',
                    action_flag=1,
                )
                saved.append((ct.pk, permission.pk, log.pk, group.pk))
        return saved

    def assert_grants(self, apps, adviser_id, saved, moved):
        get = apps.get_model
        for ct_id, permission_id, log_id, group_id in saved:
            ct = get('contenttypes', 'ContentType').objects.get(pk=ct_id)
            owner = next(
                app
                for app, names in DOMAIN_MODELS.items()
                if ct.model in {n.lower() for n in names}
            )
            self.assertEqual(ct.app_label, owner if moved else 'matching')
            permission = get('auth', 'Permission').objects.get(pk=permission_id)
            self.assertEqual(permission.content_type_id, ct_id)
            self.assertTrue(permission.group_set.filter(pk=group_id).exists())
            self.assertTrue(permission.user_set.filter(pk=adviser_id).exists())
            self.assertEqual(
                get('admin', 'LogEntry').objects.get(pk=log_id).content_type_id, ct_id
            )

    def test_populated_forward_reverse_preserves_all_tables_rows_relations_and_grants(
        self,
    ):
        old = self.migrate(BEFORE)
        adviser, candidate, review = self.seed(old)
        saved = self.grants(current_apps, adviser)
        before = self.snapshot(old, moved=False)
        new = self.migrate(AFTER)
        self.assertEqual(self.snapshot(new, moved=True), before)
        self.assert_grants(current_apps, adviser.pk, saved, moved=True)
        with connection.cursor() as cursor:
            for owner, names in DOMAIN_MODELS.items():
                for name in names:
                    table = f'{owner}_{name.lower()}'
                    constraints = connection.introspection.get_constraints(
                        cursor, table
                    )
                    self.assertTrue(
                        all(key.startswith(owner + '_') for key in constraints), table
                    )
        moved_review = new.get_model(
            'introductions', 'CandidateOfferReview'
        ).objects.get(pk=review.pk)
        self.assertEqual(moved_review.match.candidate.user_id, candidate.pk)
        self.assertEqual(moved_review.answers.get().dialogue, {'kept': True})
        with self.assertRaises(IntegrityError), transaction.atomic():
            new.get_model('introductions', 'CandidateOfferReview').objects.filter(
                pk=review.pk
            ).update(requested_by_adviser_id=candidate.pk)
        # Writes made after the move must also survive rollback with their IDs.
        new.get_model(
            'introductions', 'CandidateOfferConversationMessage'
        ).objects.create(
            conversation_id=moved_review.candidate_offer_conversation.pk,
            author_id=candidate.pk,
            body='Reply created after the extraction',
        )
        before = self.snapshot(new, moved=True)
        restored = self.migrate(BEFORE)
        self.assertEqual(self.snapshot(restored, moved=False), before)
        self.assert_grants(current_apps, adviser.pk, saved, moved=False)
        self.migrate(AFTER)
        self.assertEqual(self.snapshot(new, moved=True), before)

    def test_conflicting_content_types_abort_without_merging_permissions(self):
        old = self.migrate(BEFORE)
        ct = old.get_model('contenttypes', 'ContentType')
        ct.objects.get_or_create(app_label='matching', model='candidateofferreview')
        duplicate = ct.objects.create(
            app_label='introductions', model='candidateofferreview'
        )
        try:
            with self.assertRaisesMessage(RuntimeError, 'Conflicting content types'):
                self.migrate(AFTER)
        finally:
            ct.objects.filter(pk=duplicate.pk).delete()

    def test_targeted_migrate_completes_both_new_domains(self):
        old = self.migrate(BEFORE)
        adviser, candidate, review = self.seed(old)
        for app in ('introductions', 'followup', 'matching'):
            call_command(
                'migrate', app, interactive=False, verbosity=0, stdout=StringIO()
            )
            from eures_beta.introductions.models import CandidateOfferReview

            self.assertEqual(
                CandidateOfferReview.objects.get(pk=review.pk).requested_by_adviser_id,
                adviser.pk,
            )
            with connection.cursor() as cursor:
                for owner, names in DOMAIN_MODELS.items():
                    for name in names:
                        cursor.execute(
                            'SELECT to_regclass(%s)', [f'{owner}_{name.lower()}']
                        )
                        self.assertIsNotNone(cursor.fetchone()[0])
            self.migrate(BEFORE)
