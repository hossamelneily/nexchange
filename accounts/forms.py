# -*- coding: utf-8 -*-

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from accounts.models import Profile
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm


class CustomUserCreationForm(UserCreationForm):
    """So username is not a required field"""

    class Meta:
        model = User
        fields = ['password1', 'password2']


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['email', ]


class UserProfileForm(forms.ModelForm):
    def clean_phone(self):
        """Ensure phone is unique"""
        phone = self.cleaned_data.get('phone')
        if Profile.objects.filter(phone=phone). \
                exclude(pk=self.instance.pk).exists():
            raise ValidationError(
                u'This phone is already registered.',
                code='invalid'
            )

        return phone

    class Meta:
        model = Profile
        fields = ['phone', ]


class UpdateUserProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name']


class LoginForm(AuthenticationForm):
    """So username is labeled as 'Phone'"""

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = 'Phone'
