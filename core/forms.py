# -*- coding: utf-8 -*-
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User   # fill in custom user info then save it 
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from .models import *
from django.forms import ModelForm,Textarea,TextInput,HiddenInput, CheckboxInput
from django.forms.extras.widgets import SelectDateWidget


class UserRegistrationForm(forms.Form):
    PHONE_REGEX = r'\+[0-9]{12,}'  # pattern for a valid phone number    
    PASSWORD_REGEX = r'.*'  # pattern for a valid password
    PASSWORD_MIN_LENGTH = 8  

    phone = forms.RegexField(regex=PHONE_REGEX, required=True,
        help_text="Enter Phone in international format ex +555190099889.")
    
    password = forms.RegexField(regex=PASSWORD_REGEX, min_length=PASSWORD_MIN_LENGTH, required=True, 
        widget=forms.PasswordInput, help_text="Enter password.")
    
    password_again = forms.RegexField(regex=PASSWORD_REGEX, min_length=PASSWORD_MIN_LENGTH, required=True, 
        widget=forms.PasswordInput, help_text="Enter password again.")

    
    def clean_phone(self):
        '''Ensure phone is unique'''
        phone = self.cleaned_data.get('phone')

        if Profile.objects.filter(phone=phone).exists():
            raise ValidationError(u'This phone is already registered.',
                code='invalid',)

        return phone

    def clean(self):
        '''Ensure passwords are equal'''
        password = self.cleaned_data.get('password')
        password_again = self.cleaned_data.get('password_again')

        if password != password_again:
            self._errors["password"] = self.error_class([u'Passwords did not match.'])
            self._errors["password_again"] = self.error_class([u'Passwords did not match.'])

        return self.cleaned_data

    def save(self, request):
        phone = self.cleaned_data['phone']
        password = self.cleaned_data['password']
        user = User.objects.create_user(username=phone, email=None, password=password)
        
        # set to inative until confirmation
        user.is_active = False
        user.save()

        # create associate profile
        profile = Profile(user=user, disabled=True, phone=phone)
        profile.save()