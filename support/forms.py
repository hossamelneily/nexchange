from django import forms
from .models import Support
from orders.models import Order


class SupportForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(SupportForm, self).__init__(*args, **kwargs)
        self.fields['order'].queryset = \
            Order.objects.filter(user__username=self.request.user)
        self.fields['order'].empty_label = "--- Please choise value ---"

    class Meta:
        model = Support
        exclude = ['user', 'is_resolved', 'created']
