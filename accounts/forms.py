from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User
from .usernames import MAX_LENGTH, validate_username


def clean_unique_username(value, exclude_pk=None):
    name = validate_username(value)
    taken = User.objects.filter(username__iexact=name)
    if exclude_pk:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise forms.ValidationError(_("This username is already taken."))
    return name


def username_field():
    return forms.CharField(
        label=_("Username"),
        max_length=MAX_LENGTH,
        help_text=_("Visible to other players. 3 to 20 characters: letters, digits, “_” and “-”."),
        widget=forms.TextInput(attrs={"autocomplete": "username", "autocapitalize": "none", "spellcheck": "false"}),
    )


class SignupForm(BaseUserCreationForm):
    """Email, public username and password."""

    username = username_field()

    class Meta:
        model = User
        fields = ["email", "username"]

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

    def clean_username(self):
        return clean_unique_username(self.cleaned_data.get("username"))


class UsernameForm(forms.Form):
    """Choose or change the public username."""

    username = username_field()

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user.username and not self.is_bound:
            self.initial["username"] = user.username

    def clean_username(self):
        return clean_unique_username(self.cleaned_data.get("username"), exclude_pk=self.user.pk)

    def save(self):
        self.user.username = self.cleaned_data["username"]
        self.user.save(update_fields=["username"])
        return self.user


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
