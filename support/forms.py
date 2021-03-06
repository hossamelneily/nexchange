from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _

from accounts.models import Profile
from orders.models import Order

from .models import Support


class SupportForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(SupportForm, self).__init__(*args, **kwargs)
        self.fields['order'].queryset = \
            Order.objects.filter(user__username=self.request.user)
        self.fields['order'].empty_label = _(
            '--- Please select an order (if applicable) ---')
        self.fields['order'].help_text = \
            _('Choose an order which is related to your request')

        try:
            profile = Profile.objects.get(user__username=self.request.user)
            self.fields['telephone'].initial = profile.phone
            user = User.objects.get(username=self.request.user)
            self.fields['email'].initial = user.email
        except ObjectDoesNotExist:
            pass

    class Meta:
        model = Support
        exclude = ['user', 'is_resolved', 'created']
