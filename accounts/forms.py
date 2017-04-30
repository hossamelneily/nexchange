# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from accounts.models import NexchangeUser as User
from accounts.models import Profile
from django.utils.translation import ugettext_lazy as _


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
        fields = ['first_name', 'last_name',
                  'notify_by_email', 'notify_by_phone', 'affiliate_address']

    def __init__(self, *args, **kwargs):
        super(UpdateUserProfileForm, self).__init__(*args, **kwargs)
        self._edit_affiliate_address_field()

    def _edit_affiliate_address_field(self):
        affiliate_address = self.fields['affiliate_address']
        affiliate_address.queryset = self.instance.owned_withdraw_addresses
        affiliate_address.required = False
        affiliate_address.label = _('Affiliate Address')
        affiliate_address.help_text = _(
            'Contact support to change Affiliate Address.'
        )
        affiliate_address.help_text = _(
            'To become affiliate you need to complete at least one order '
            'with withdraw address (Buy Crypto currency from us).')
        affiliate_address.widget.attrs['disabled'] = True
        # User already has an address
        if self.instance.affiliate_address:
            affiliate_address.help_text = _('Contact support to change '
                                            'Affiliate Address.')
        # User has at least one COMPLETED orders
        elif len(self.instance.completed_orders) > 0:
            # User has withdraw addresses
            if len(self.instance.owned_withdraw_addresses) > 0:
                affiliate_address.widget.attrs['disabled'] =\
                    False
                affiliate_address.help_text = _(
                    'Select your Affiliate Address.')


class LoginForm(AuthenticationForm):
    """So username is labeled as 'Phone'"""

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = 'Phone'
