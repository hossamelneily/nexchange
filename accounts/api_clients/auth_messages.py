from django.conf import settings
from accounts.models import SmsToken
from nexchange.utils import _send_sms, send_email


class AuthMessages:

    def __init__(self, us_phone=settings.TWILIO_PHONE_FROM_US,
                 uk_phone=settings.TWILIO_PHONE_FROM_UK,
                 msg_template=settings.SMS_MESSAGE_AUTH):
        self.us_phone = us_phone
        self.uk_phone = uk_phone
        self.msg_template = msg_template

    def create_token(self, user):
        token = SmsToken(user=user, send_count=1)
        token.save()
        return token

    def get_or_create_token(self, user):
        try:
            token = SmsToken.objects.filter(user=user).latest('id')
            token.send_count += 1
            token.save()
        except SmsToken.DoesNotExist:
            token = self.create_token(user)
        if not token.valid:
            token = self.create_token(user)
        return token

    def create_auth_msg(self, user):
        token = self.get_or_create_token(user)
        msg = self.msg_template.format(token.sms_token)
        return msg

    def send_auth_msg(self, user, type='sms'):
        msg = self.create_auth_msg(user)
        if type == 'sms':
            to = str(user.profile.phone)
            if to.startswith('+1'):
                from_phone = self.us_phone
            else:
                from_phone = self.uk_phone
            message = _send_sms(msg, to, from_phone)
        elif type == 'email':
            to = user.email
            message = send_email(to, msg=msg)
        else:
            message = 'msg type : {} does not exist'
        return message

    def send_auth_sms(self, user):
        return self.send_auth_msg(user, type='sms')

    def send_auth_email(self, user):
        return self.send_auth_msg(user, type='email')
