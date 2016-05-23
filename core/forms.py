# -*- coding: utf-8 -*-
from django import forms
# fill in custom user info then save it
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from models import *
from django.forms import ModelForm, Textarea, TextInput, HiddenInput, CheckboxInput
from django.forms.extras.widgets import SelectDateWidget


class DateSearchForm(forms.Form):
    date = forms.DateField(required=False, label="Search by Date")
