from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class SignupForm(BaseUserCreationForm):
    """Email + password, nothing else."""

    class Meta:
        model = User
        fields = ["email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(autocomplete="email", autofocus=True)
        self.fields["password1"].help_text = password_validation.password_validators_help_text_html()
        self.fields["password2"].label = _("Confirm password")
        self.fields["password2"].help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account already exists with this email."))
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Email")
        self.fields["username"].widget = forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True})

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(_("Wrong password."))
        return password
