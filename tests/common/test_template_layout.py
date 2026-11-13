from unittest import TestCase

from eures_beta.template_layout import compact_lines


class TemplateLayoutTests(TestCase):
    def test_compact_django_form_is_reported(self):
        source = '<form action="{% url \'set_language\' %}">' + '{% csrf_token %}'
        source += '<label>Language</label><select>' + ' ' * 120 + '</select></form>'
        self.assertEqual(compact_lines(source), [1])

    def test_multiline_layout_and_indivisible_messages_are_allowed(self):
        source = '<form>\n<label>{% translate "' + 'long message ' * 20
        source += '" %}</label>\n<select></select>\n</form>'
        self.assertEqual(compact_lines(source), [])

    def test_html_examples_inside_scripts_are_not_markup(self):
        source = '<script>const text = "<div><input>' + 'x' * 150 + '";</script>'
        self.assertEqual(compact_lines(source), [])
