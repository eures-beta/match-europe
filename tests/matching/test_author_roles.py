"""Author roles are invariants, including writes bypassing model.save()."""

from io import StringIO

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from eures_beta.candidates.models import CandidateProfile
from eures_beta.matching import services
from eures_beta.matching.models import (
    CandidateOfferReview,
    CandidateOfferReviewAnswer,
    CandidateProfileSharing,
    MatchDecision,
)
from eures_beta.users.models import User

DEMO = dict(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)


@override_settings(**DEMO)
class AuthorRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())

    def setUp(self):
        self.review = CandidateOfferReview.objects.select_related(
            'match__candidate__user', 'match__offer__employer'
        ).first()
        self.match = self.review.match
        self.adviser = self.review.requested_by_adviser
        self.candidate = self.match.candidate.user
        self.employer = self.match.offer.employer

    def test_decision_service_requires_an_active_adviser(self):
        before = self.match.decisions.count()
        evaluation = self.match.evaluations.latest('pk')
        for user in (self.candidate, self.employer, None):
            with self.subTest(user=user), self.assertRaises(PermissionDenied):
                services.decide(
                    self.match.pk, evaluation.pk, 'refused', by_adviser=user
                )
        self.adviser.is_active = False
        self.adviser.save(update_fields=['is_active'])
        with self.assertRaises(PermissionDenied):
            services.decide(
                self.match.pk, evaluation.pk, 'refused', by_adviser=self.adviser
            )
        self.assertEqual(self.match.decisions.count(), before)

    def test_database_refuses_decision_authors_of_other_roles_and_missing_author(self):
        decision = self.match.decisions.first()
        for user in (self.candidate, self.employer, None):
            with (
                self.subTest(user=user),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                MatchDecision.objects.filter(pk=decision.pk).update(by_adviser=user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MatchDecision.objects.bulk_create(
                [
                    MatchDecision(
                        match=self.match,
                        evaluation=decision.evaluation,
                        value='refused',
                    )
                ]
            )
        with self.assertRaises(ValidationError):
            MatchDecision.objects.create(
                match=self.match, evaluation=decision.evaluation, value='refused'
            )
        decision.refresh_from_db()
        self.assertEqual(decision.by_adviser, self.adviser)

    def test_database_refuses_review_requester_of_other_roles(self):
        for user in (self.candidate, self.employer):
            with (
                self.subTest(user=user),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                CandidateOfferReview.objects.filter(pk=self.review.pk).update(
                    requested_by_adviser=user
                )
        self.review.refresh_from_db()
        self.assertEqual(self.review.requested_by_adviser, self.adviser)

    def test_profile_owner_cannot_change_by_save_or_direct_database_write(self):
        other = User.objects.create_user(
            'other-candidate@roles.invalid', kind='candidate'
        )
        profile = self.match.candidate
        profile.user = other
        with self.assertRaises(ValidationError):
            profile.save()
        for user in (other, self.adviser, self.employer):
            with (
                self.subTest(user=user),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                CandidateProfile.objects.filter(pk=profile.pk).update(user=user)
        profile.refresh_from_db()
        self.assertEqual(profile.user, self.candidate)

    def test_database_refuses_new_profile_for_wrong_role_even_with_bulk_create(self):
        profile = self.match.candidate
        for user in (self.adviser, self.employer):
            copy = CandidateProfile(
                **{
                    field.attname: getattr(profile, field.attname)
                    for field in profile._meta.fields
                    if field.name not in ('id', 'user')
                },
                user=user,
            )
            with (
                self.subTest(user=user),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                CandidateProfile.objects.bulk_create([copy])

    def test_candidate_authors_are_derived_without_a_second_stored_identity(self):
        for model in (CandidateOfferReviewAnswer, CandidateProfileSharing):
            self.assertNotIn('actor', {f.name for f in model._meta.fields})
        self.assertEqual(self.review.match.candidate.user, self.candidate)


@override_settings(**DEMO)
class AuthorRoleMigrationTests(TransactionTestCase):
    before = '0021_move_profile_review_suggestion'
    after = '0022_explicit_author_roles'

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([('matching', target)])
        return executor.loader.project_state([('matching', target)]).apps

    def setUp(self):
        call_command('seed_test_accounts', minimal=True, stdout=StringIO())
        self.review_id = CandidateOfferReview.objects.first().pk
        self.old = self.migrate(self.before)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_nonempty_roundtrip_preserves_decisions_answers_consents_and_unknowns(self):
        Review = self.old.get_model('matching', 'CandidateOfferReview')
        Decision = self.old.get_model('matching', 'MatchDecision')
        review = Review.objects.get(pk=self.review_id)
        evaluation = review.match.evaluations.first()
        unknown = Decision.objects.create(
            match_id=review.match_id, evaluation_id=evaluation.pk, value='refused'
        )
        rows = []
        for name in ('CandidateOfferReviewAnswer', 'CandidateProfileSharing'):
            kwargs = dict(
                review_id=review.pk,
                actor_id=review.match.candidate.user_id,
                fingerprint='a' * 64,
            )
            kwargs.update(
                dict(question_key='test', presented={'preserved': True}, value='yes')
                if name.endswith('Answer')
                else dict(agreed=False)
            )
            row = self.old.get_model('matching', name).objects.create(**kwargs)
            rows.append((name, row.pk, row.created_at))
        decision = Decision.objects.exclude(pk=unknown.pk).first()
        adviser_id = review.requested_by_id
        new = self.migrate(self.after)
        NewDecision = new.get_model('matching', 'MatchDecision')
        self.assertEqual(
            NewDecision.objects.get(pk=decision.pk).by_adviser_id, adviser_id
        )
        self.assertIsNone(NewDecision.objects.get(pk=unknown.pk).by_adviser_id)
        self.assertEqual(
            new.get_model('matching', 'CandidateOfferReview')
            .objects.get(pk=review.pk)
            .requested_by_adviser_id,
            adviser_id,
        )
        for name, pk, date in rows:
            row = new.get_model('matching', name).objects.get(pk=pk)
            self.assertEqual(row.created_at, date)
            self.assertEqual(row.fingerprint, 'a' * 64)
        old = self.migrate(self.before)
        self.assertEqual(
            old.get_model('matching', 'MatchDecision')
            .objects.get(pk=decision.pk)
            .actor,
            f'adviser:{adviser_id}',
        )
        self.assertEqual(
            old.get_model('matching', 'MatchDecision').objects.get(pk=unknown.pk).actor,
            'local_operator',
        )
        for name, pk, _ in rows:
            self.assertEqual(
                old.get_model('matching', name).objects.get(pk=pk).actor_id,
                review.match.candidate.user_id,
            )
        self.migrate(self.after)

    def test_migration_rejects_invalid_decision_author_without_discarding_it(self):
        Decision = self.old.get_model('matching', 'MatchDecision')
        decision = Decision.objects.first()
        original = decision.actor
        candidate_id = (
            self.old.get_model('matching', 'CandidateOfferReview')
            .objects.get(pk=self.review_id)
            .match.candidate.user_id
        )
        for text in ('unrecognized', 'adviser:999999999', f'adviser:{candidate_id}'):
            Decision.objects.filter(pk=decision.pk).update(actor=text)
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                self.migrate(self.after)
            self.assertEqual(Decision.objects.get(pk=decision.pk).actor, text)
        Decision.objects.filter(pk=decision.pk).update(actor=original)

    def test_migration_rejects_conflicting_candidate_author_and_wrong_requester(self):
        Review = self.old.get_model('matching', 'CandidateOfferReview')
        review = Review.objects.get(pk=self.review_id)
        adviser_id = review.requested_by_id
        candidate_id = review.match.candidate.user_id
        for name in ('CandidateOfferReviewAnswer', 'CandidateProfileSharing'):
            Model = self.old.get_model('matching', name)
            kwargs = dict(
                review_id=review.pk, actor_id=adviser_id, fingerprint='a' * 64
            )
            kwargs.update(
                dict(question_key='test', presented={}, value='yes')
                if name.endswith('Answer')
                else dict(agreed=False)
            )
            row = Model.objects.create(**kwargs)
            with self.subTest(model=name), self.assertRaises(RuntimeError):
                self.migrate(self.after)
            self.assertEqual(Model.objects.get(pk=row.pk).actor_id, adviser_id)
            Model.objects.filter(pk=row.pk).update(actor_id=candidate_id)
        Review.objects.filter(pk=review.pk).update(requested_by_id=candidate_id)
        with self.assertRaises(RuntimeError):
            self.migrate(self.after)
        Review.objects.filter(pk=review.pk).update(requested_by_id=adviser_id)

    def test_profile_migration_adds_immutable_ownership_without_changing_the_owner(
        self,
    ):
        executor = MigrationExecutor(connection)
        targets = [('candidates', '0010_move_profile_review_suggestion')]
        executor.migrate(targets)
        old = executor.loader.project_state(targets).apps
        Profile = old.get_model('candidates', 'CandidateProfile')
        profile = Profile.objects.first()
        owner_id = profile.user_id
        other = old.get_model('users', 'User').objects.create(
            email='another-owner@roles.invalid', kind='candidate'
        )
        # The old schema checked the role, but still allowed another candidate.
        Profile.objects.filter(pk=profile.pk).update(user_id=other.pk)
        Profile.objects.filter(pk=profile.pk).update(user_id=owner_id)
        new = self.migrate(self.after)
        Profile = new.get_model('candidates', 'CandidateProfile')
        with self.assertRaises(DatabaseError), transaction.atomic():
            Profile.objects.filter(pk=profile.pk).update(user_id=other.pk)
        self.assertEqual(Profile.objects.get(pk=profile.pk).user_id, owner_id)
