from django.core import mail
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings

from eures_beta.emails.rendering import html_email
from tests.emails.assertions import Links, assert_clickable_email


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class HtmlEmailTests(SimpleTestCase):
    def test_long_signed_urls_survive_html_and_mime_in_all_languages(self):
        link = (
            "https://example.invalid/accounts/confirm/?sesame="
            + "aB_0-" * 180
            + ":signed:token&next=%2Fcandidate%2Foffer%2F%3Flang%3Dfr"
        )
        for language in ("fr", "en", "de"):
            with self.subTest(language=language):
                body = "A personal link:\n" + link + "\n\nDo not forward it."
                html = html_email(body, language=language)
                self.assertIn(f'lang="{language}"', html)
                send_mail(
                    "Match Europe",
                    body,
                    "sender@example.invalid",
                    ["recipient@example.invalid"],
                    html_message=html,
                )
                assert_clickable_email(self, mail.outbox[-1])

    def test_html_looking_user_text_is_escaped_and_cannot_inject_an_anchor(self):
        html = html_email(
            '<script>alert(1)</script><a href="javascript:alert(1)">Click</a>\n'
            "https://example.invalid/confirm/?token=abc&next=%2F"
        )
        self.assertNotIn("<script>", html)
        self.assertEqual(
            Links(html).hrefs,
            ["https://example.invalid/confirm/?token=abc&next=%2F"],
        )

    def test_fallback_is_translated_and_keeps_the_complete_url(self):
        for language, wording in (
            ("fr", "Si un lien n’est pas cliquable"),
            ("en", "If a link cannot be clicked"),
            ("de", "Falls ein Link nicht anklickbar ist"),
        ):
            with self.subTest(language=language):
                self.assertIn(wording, html_email("Message", language=language))

    def test_every_rich_invitation_keeps_a_visible_copyable_personal_url(self):
        link = "https://example.invalid/invitations/confirm/?invitation=abc&part=def"
        for template in (
            "adviser/invitation",
            "candidate/invitation",
            "candidate/reminder",
            "employer/invitation",
            "employer/reminder",
        ):
            with self.subTest(template=template):
                html = render_to_string(
                    f"invitations/emails/{template}.html",
                    {"link": link, "privacy": "https://example.invalid/privacy/"},
                )
                # The main action and the copyable fallback address target the same URL.
                self.assertEqual(Links(html).hrefs.count(link), 2)
                self.assertIn("https://example.invalid/invitations/confirm/", html)
