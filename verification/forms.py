from django import forms

from verification.models import Verification


class VerificationUploadForm(forms.ModelForm):

    class Meta:
        model = Verification
        fields = ['identity_document', 'utility_document']
