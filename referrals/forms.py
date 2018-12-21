# -*- coding: utf-8 -*-

from django import forms

from referrals.models import ReferralCode
from django.utils.translation import ugettext_lazy as _


class ReferralTokenForm(forms.ModelForm):

    class Meta:
        model = ReferralCode
        fields = ['code', 'link', 'comment']

    comment = forms.CharField(
        label=_('Name / Short Comment'),
        required=False,
        help_text=_('This field can be used to describe the purpose and target'
                    ' public of this Referral Link')
    )
    link = forms.CharField(
        label=_('Referral Link'),
        required=False,
        help_text=_('Use this link to refer users to n.exchange and receive a'
                    ' commission!'),
        widget=forms.TextInput(attrs={'disabled': 'disabled'})
    )
    code = forms.CharField(
        label=_('Referral Code'),
        required=False,
        help_text=_('A code to distinct your referrals from other users'),
        widget=forms.TextInput(attrs={'disabled': 'disabled'})
    )
