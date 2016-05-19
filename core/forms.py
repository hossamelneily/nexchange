# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User   # fill in custom user info then save it 
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from models import *
from django.forms import ModelForm,Textarea,TextInput,HiddenInput, CheckboxInput
from django.forms.extras.widgets import SelectDateWidget
