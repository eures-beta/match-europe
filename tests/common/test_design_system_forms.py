from django import forms
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from eures_beta.www.design_system import bootstrap_form


class SampleForm(forms.Form):
    name = forms.CharField(help_text='Shown to advisers.')
    kind = forms.ChoiceField(choices=[('a', 'A'), ('b', 'B')])
    tags = forms.MultipleChoiceField(
        choices=[('x', 'X'), ('y', 'Y')],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    note = forms.CharField(widget=forms.Textarea, required=False)
    secret = forms.CharField(widget=forms.HiddenInput, required=False)


class DesignSystemFormTests(SimpleTestCase):
    def test_each_widget_gets_its_bootstrap_class(self):
        form = bootstrap_form(SampleForm())
        classes = {name: f.widget.attrs.get('class') for name, f in form.fields.items()}
        self.assertEqual(
            classes,
            {
                'name': 'form-control',
                'kind': 'form-select',
                'tags': 'form-check-input',
                'note': 'form-control',
                'secret': None,
            },
        )
        self.assertEqual(
            form.fields['name'].widget.attrs['aria-describedby'], 'id_name-help'
        )

    def test_invalid_fields_are_marked_and_the_class_is_not_shared(self):
        form = bootstrap_form(SampleForm({'kind': 'a'}))
        self.assertIn('is-invalid', form.fields['name'].widget.attrs['class'])
        self.assertEqual(form.fields['name'].widget.attrs['aria-invalid'], 'true')
        self.assertNotIn('is-invalid', form.fields['kind'].widget.attrs['class'])
        self.assertNotIn('class', SampleForm().fields['name'].widget.attrs)

    def test_field_include_renders_label_help_errors_and_checkboxes(self):
        form = bootstrap_form(SampleForm({'kind': 'a'}))
        html = render_to_string('eures/form_field.html', {'field': form['name']})
        self.assertInHTML('<label class="form-label" for="id_name">Name</label>', html)
        self.assertIn('<div class="form-text" id="id_name-help">', html)
        self.assertIn('class="invalid-feedback"', html)
        html = render_to_string('eures/form_field.html', {'field': form['tags']})
        self.assertIn('<legend class="form-label fs-6">Tags</legend>', html)
        self.assertInHTML(
            '<label class="form-check-label" for="id_tags_0">X</label>', html
        )
