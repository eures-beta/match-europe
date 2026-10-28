from django import forms
from django.utils.translation import gettext_lazy as _


class EmployerContactForm(forms.Form):
    name = forms.CharField(label=_('Contact name'), max_length=150)
    email = forms.EmailField(label=_('Contact email'), max_length=254)
    phone = forms.CharField(label=_('Phone (optional)'), max_length=40, required=False)
    function = forms.CharField(
        label=_('Role in the company (optional)'), max_length=150, required=False
    )


class ImportAssignmentForm(forms.Form):
    adviser = forms.ModelChoiceField(
        label=_('Adviser responsible for this offer'),
        queryset=None,
        required=False,
        empty_label=_('Unassigned'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model

        self.fields['adviser'].queryset = (
            get_user_model()
            .objects.filter(
                is_active=True, profile__role='adviser', profile__verified=True
            )
            .select_related('profile')
            .order_by('profile__name', 'pk')
        )
        self.fields['adviser'].label_from_instance = (
            lambda user: user.profile.name or user.username
        )
