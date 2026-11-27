"""Shared Bootstrap widget presentation, independent of the component catalogue."""

from django import forms


def bootstrap_form(form):
    """Give each visible widget its Bootstrap class; mark invalid fields and link help texts."""
    errors = form.errors if form.is_bound else {}
    for name, field in form.fields.items():
        widget = field.widget
        if isinstance(widget, forms.HiddenInput):
            continue
        if isinstance(widget, (forms.RadioSelect, forms.CheckboxInput)):
            css = 'form-check-input'  # CheckboxSelectMultiple is a RadioSelect
        elif isinstance(widget, forms.Select):
            css = 'form-select'
        else:
            css = 'form-control'
        classes = widget.attrs.get('class', '').split() + [css]
        if name in errors:
            classes.append('is-invalid')
            widget.attrs['aria-invalid'] = 'true'
        widget.attrs['class'] = ' '.join(dict.fromkeys(classes))
        if field.help_text:
            widget.attrs['aria-describedby'] = form[name].auto_id + '-help'
    return form
