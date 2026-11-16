"""Naming checks run with Django checks, without a database connection."""

from unittest.mock import patch
from django.test import SimpleTestCase
from config.model_naming import check_model_names, schema_prefix
from django.db.models import Index
from eures_beta.employers.models import Company, CompanyMembership


class ModelNamingChecksTests(SimpleTestCase):
    def test_current_model_contracts_are_coherent(self):
        self.assertEqual(check_model_names(), [])

    def test_legacy_table_is_rejected(self):
        with patch.object(Company._meta, 'db_table', 'journeys_employercompany'):
            self.assertIn('model_names.E001', {e.id for e in check_model_names()})

    def test_constraint_must_follow_model_name(self):
        constraint = CompanyMembership._meta.constraints[0]
        with patch.object(constraint, 'name', 'unique_employer_membership'):
            self.assertIn('model_names.E002', {e.id for e in check_model_names()})

    def test_relationship_and_reverse_relationship_are_checked(self):
        field = CompanyMembership._meta.get_field('user')
        with patch.object(field, 'name', 'person'):
            self.assertIn('model_names.E003', {e.id for e in check_model_names()})
        with patch.object(field.remote_field, 'related_name', 'imports'):
            self.assertIn('model_names.E004', {e.id for e in check_model_names()})

    def test_legacy_column_name_is_rejected(self):
        field = CompanyMembership._meta.get_field('user')
        with patch.object(field, 'column', 'person_id'):
            self.assertIn('model_names.E005', {e.id for e in check_model_names()})

    def test_long_model_index_names_fit_django_limit_and_follow_model(self):
        table = CompanyMembership._meta.db_table
        prefix = schema_prefix(table, 30)
        self.assertNotEqual(prefix, schema_prefix('journeys_employermembership', 30))
        index = Index(fields=['user'], name=prefix + 'user_idx')
        self.assertLessEqual(len(index.name), index.max_name_length)
        with patch.object(CompanyMembership._meta, 'indexes', [index]):
            self.assertEqual(check_model_names(), [])
            with patch.object(index, 'name', 'journeys_membership_user_idx'):
                self.assertIn('model_names.E002', {e.id for e in check_model_names()})
