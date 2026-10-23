"""Integration checks for the combined employer rehearsal behind HTTPS."""

import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import EmployerImport, EmployerSearchOperation


@override_settings(SHARED_DEMO=True, SECURE_SSL_REDIRECT=False)
@patch.dict(
    "os.environ",
    {
        "ME_EMPLOYER_EMAIL_LOCAL": "0",
        "ME_LOCAL_REVIEW_ONLY": "0",
        "ME_EMPLOYER_SEARCH_SIMULATION": "0",
    },
)
class ConsolidatedDemoTests(TestCase):
    def sign_in(self, client, email):
        self.assertEqual(
            client.post("/employer/access/", {"email": email}, secure=True).status_code,
            302,
        )
        link = client.session["employer_test_message"]["link"]
        self.assertEqual(client.post(link, secure=True).status_code, 302)

    def create_offer(self, client):
        response = client.post(
            "/local-api/imports/",
            {
                "kind": "manual",
                "text": "Fictional technician in Metz.",
                "agreement": "true",
                "email": "fictional@example.invalid",
                "contact": json.dumps(
                    {"name": "Fictional contact", "email": "contact@example.invalid"}
                ),
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["localOnly"])
        self.assertEqual(response.json()["login_url"], "/employer/connected/")
        self.assertEqual(
            client.post(
                "/employer/attach/", {"name": "Fictional establishment"}, secure=True
            ).status_code,
            302,
        )
        return EmployerImport.objects.get(pk=response.json()["id"])

    def test_https_import_account_attachment_search_and_duplication(self):
        with (
            patch(
                "journeys.employer_api.aglae",
                side_effect=AssertionError("External write"),
            ),
            patch(
                "journeys.employer_api.geocode", side_effect=AssertionError("Geocoding")
            ),
        ):
            self.sign_in(self.client, "combined@example.invalid")
            offer = self.create_offer(self.client)
            self.assertContains(
                self.client.get("/employer/offers/", secure=True),
                "Fictional establishment",
            )
            response = self.client.get(
                reverse("employer_offer", args=[offer.pk]), secure=True
            )
            self.assertContains(
                response, reverse("employer_search_launch", args=[offer.pk])
            )
            response = self.client.post(
                reverse("employer_search_launch", args=[offer.pk]),
                {"revision": offer.revision, "confirmed": "on", "scenario": "success"},
                secure=True,
            )
            self.assertEqual(response.status_code, 302)
            offer.refresh_from_db()
            self.assertIsNotNone(offer.search_started_at)
            self.assertEqual(EmployerSearchOperation.objects.get().state, "started")
            self.assertEqual(
                self.client.post(
                    reverse("employer_offer_edit", args=[offer.pk]), {}, secure=True
                ).status_code,
                409,
            )
            response = self.client.post(
                reverse("employer_offer_duplicate", args=[offer.pk]),
                {"revision": offer.revision},
                secure=True,
            )
            self.assertEqual(response.status_code, 302)
            copy = EmployerImport.objects.exclude(pk=offer.pk).get()
            self.assertEqual(copy.duplicated_from, offer)
            self.assertIsNone(copy.search_started_at)

    def test_distinct_sessions_do_not_share_inbox_or_establishment_rights(self):
        self.sign_in(self.client, "first-demo@example.invalid")
        offer = self.create_offer(self.client)
        other = Client()
        self.assertNotContains(
            other.get("/employer/test-inbox/", secure=True),
            "first-demo@example.invalid",
        )
        self.sign_in(other, "second-demo@example.invalid")
        self.assertEqual(
            other.get(
                reverse("employer_offer", args=[offer.pk]), secure=True
            ).status_code,
            404,
        )
        self.assertNotContains(
            other.get("/employer/offers/", secure=True), "Fictional establishment"
        )

    def test_https_required_and_csrf_protects_email_and_search(self):
        self.assertEqual(self.client.get("/employer/access/").status_code, 404)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                "/employer/access/", {"email": "csrf@example.invalid"}, secure=True
            ).status_code,
            403,
        )
        self.sign_in(self.client, "csrf-owner@example.invalid")
        offer = self.create_offer(self.client)
        client.cookies = self.client.cookies.copy()
        self.assertEqual(
            client.post(
                reverse("employer_search_launch", args=[offer.pk]),
                {"revision": offer.revision, "confirmed": "on", "scenario": "success"},
                secure=True,
            ).status_code,
            403,
        )
        self.assertFalse(EmployerSearchOperation.objects.exists())
