from django.core import mail
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings
from django.utils.safestring import mark_safe

from eures_beta.emails.rendering import html_email, presentation_context
from tests.emails.assertions import Links, assert_clickable_email


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class HtmlEmailTests(SimpleTestCase):
    def test_subject_is_a_heading_without_repeating_the_first_paragraph(self):
        body = 'Unique subject\n\nKeep this paragraph.'
        html = html_email(body, subject='Unique subject')
        self.assertEqual(html.count('Unique subject'), 2)  # Document title and h1.
        self.assertIn('Keep this paragraph.', html)

    @override_settings(
        LOGIN_EMAIL_ORIGIN='https://example.invalid', ALLOWED_HOSTS=['example.invalid']
    )
    def test_common_card_keeps_plain_text_and_uses_only_trusted_brand_assets(self):
        link = 'https://example.invalid/accounts/confirm/?sesame=abc&next=%2F'
        body = 'A personal link:\n' + link
        html = html_email(
            body, subject='Your sign-in link', link=link, action_label='Sign in'
        )
        send_mail(
            'Your sign-in link',
            body,
            'sender@example.invalid',
            ['recipient@example.invalid'],
            html_message=html,
        )
        message = mail.outbox[-1]
        self.assertEqual(message.body, body)
        assert_clickable_email(self, message)
        self.assertIn('<h1', html)
        self.assertIn('Your sign-in link', html)
        self.assertIn('max-width:640px', html)
        self.assertIn('font-family:Arial', html)
        self.assertIn('https://example.invalid/privacy/', Links(html).hrefs)
        for filename in (
            'eures-ela.jpg',
            'france-travail-email.png',
            'adem.png',
            'forem.png',
        ):
            self.assertIn(filename, html)
        self.assertNotIn('<script', html)
        self.assertNotIn('<link ', html)

    @override_settings(
        LOGIN_EMAIL_ORIGIN='https://untrusted.invalid',
        ALLOWED_HOSTS=['example.invalid'],
    )
    def test_untrusted_origin_never_becomes_a_footer_destination(self):
        html = html_email('A message', subject=mark_safe('<script>bad</script>'))
        self.assertNotIn('untrusted.invalid', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_long_signed_urls_survive_html_and_mime_in_all_languages(self):
        link = (
            "https://example.invalid/accounts/confirm/?sesame="
            + "aB_0-" * 180
            + ":signed:token&next=%2Fcandidate%2Foffer%2F%3Flang%3Dfr"
        )
        for language in ("fr", "en", "de"):
            with self.subTest(language=language):
                body = "A personal link:\n" + link + "\n\nDo not forward it."
                html = html_email(
                    body, language=language, link=link, action_label='Sign in'
                )
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

    def test_rendered_plain_text_is_escaped_even_when_django_marks_it_safe(self):
        body = mark_safe(
            '<a href="javascript:alert(1)">Untrusted name</a>\n'
            "https://example.invalid/confirm/?token=abc&next=%2F"
        )
        html = html_email(body)
        self.assertIn("&lt;a", html)
        self.assertEqual(
            Links(html).hrefs,
            ["https://example.invalid/confirm/?token=abc&next=%2F"],
        )

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
                    {**presentation_context('https://example.invalid'), "link": link},
                )
                # The main action and the copyable fallback address target the same URL.
                self.assertEqual(Links(html).hrefs.count(link), 2)
                self.assertIn("https://example.invalid/invitations/confirm/", html)
                self.assertEqual(html.count('<!DOCTYPE html>'), 1)
                self.assertIn('max-width:640px', html)
                self.assertIn('france-travail-email.png', html)
