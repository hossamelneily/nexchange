# -*- coding: utf-8 -*-
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User   # fill in custom user info then save it 
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import *
from django.forms import ModelForm,Textarea,TextInput,HiddenInput, CheckboxInput
from django.forms.extras.widgets import SelectDateWidget
from django.forms import inlineformset_factory

class DateSearchForm(forms.Form):
 	date = forms.DateField(required=False, label="Search by Date") 


class UserProfileForm(forms.ModelForm):
    def clean_phone(self):
        '''Ensure phone is unique'''
        phone = self.cleaned_data.get('phone')
        if Profile.objects.filter(phone=phone).exists():
            raise ValidationError(u'This phone is already registered.',
                code='invalid',)

        return phone

    class Meta:
        model = Profile
        fields = ['phone',]


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['password1', 'password2']

