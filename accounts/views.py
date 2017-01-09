import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, JsonResponse, \
    HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from phonenumber_field.validators import validate_international_phonenumber
from twilio.exceptions import TwilioException
from twilio.rest import TwilioRestClient
import json

from accounts.forms import (CustomUserCreationForm, UpdateUserProfileForm,
                            UserForm, UserProfileForm)
from accounts.models import NexchangeUser as User
from accounts.models import Profile, SmsToken
from core.models import Address
from core.validators import validate_bc
from referrals.forms import ReferralTokenForm
from accounts.decoratos import not_logged_in_required


def user_registration(request):
    template = 'accounts/user_registration.html'
    success_message = _(
        'Registration completed. Check your phone for SMS confirmation code.')
    error_message = _('Error during accounts. <br>Details: {}')

    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic(using='default'):
                    user = user_form.save(commit=False)
                    user.username = profile_form.cleaned_data['phone']
                    user.save()

                    profile_form = UserProfileForm(
                        request.POST, instance=user.profile)
                    profile = profile_form.save(commit=False)
                    profile.disabled = True
                    profile.save()
                    res = _send_sms(user)
                    assert res
                    if settings.DEBUG:
                        print(res)

                    messages.success(request, success_message)

                user = authenticate(
                    username=user.username,
                    password=user_form.cleaned_data['password1'])
                login(request, user)

                return redirect(reverse('accounts.user_profile'))

            except Exception as e:
                msg = error_message.format(e)
                messages.error(request, msg)

    else:
        user_form = CustomUserCreationForm()
        profile_form = UserProfileForm()

    return render(
        request, template, {
            'user_form': user_form, 'profile_form': profile_form})


@method_decorator(login_required, name='dispatch')
class UserUpdateView(View):

    def get(self, request):
        user_form = UserForm(
            instance=self.request.user)
        profile_form = UpdateUserProfileForm(
            instance=self.request.user.profile)
        referral_form = ReferralTokenForm(
            instance=self.request.user.referral_code.get())

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'referral_form': referral_form,
        }

        return render(request, 'accounts/user_profile.html', context)

    def post(self, request):
        user_form = \
            UserForm(request.POST,
                     instance=self.request.user)
        profile_form = \
            UpdateUserProfileForm(request.POST,
                                  instance=self.request.user.profile)
        referral_form = \
            ReferralTokenForm(request.POST,
                              instance=self.request.user.referral_code.get())
        success_message = _('Profile updated with success')

        if user_form.is_valid() and \
                profile_form.is_valid():
            user_form.save()
            profile_form.save()
            # referral_form.save()
            messages.success(self.request, success_message)

            return redirect(reverse('accounts.user_profile'))
        else:
            ctx = {
                'user_form': user_form,
                'profile_form': profile_form,
                'referral_form': referral_form
            }

            return render(request, 'accounts/user_profile.html', ctx, )


def _send_sms(user, token=None):
    if token is None:
        token = SmsToken.objects.filter(user=user).latest('id')

    msg = _("BTC Exchange code:") + ' %s' % token.sms_token
    phone_to = str(user.username)

    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=msg, to=phone_to, from_=settings.TWILIO_PHONE_FROM)
        return message
    except TwilioException as err:
        return err


def resend_sms(request):
    phone = request.POST.get('phone')
    if request.user.is_anonymous() and phone:
        user = User.objects.get(profile__phone=phone)
    else:
        user = request.user
    message = _send_sms(user)
    return JsonResponse({'message_sid': message.sid}, safe=False)


def verify_phone(request):
    def render_response(msg, code):
        _context = {
            'status': 'Error' if code > 201 else 'OK',
            'message':
                str(_(msg))
        }
        return HttpResponse(
            json.dumps(_context),
            status=code,
            content_type='application/json'
        )

    sent_token = request.POST.get('token')
    sent_token = re.sub(' +', '', sent_token)
    phone = request.POST.get('phone')
    phone = re.sub(' +', '', phone)
    anonymous = request.user.is_anonymous()
    if anonymous and phone:
        try:
            user = User.objects.get(username=phone)
        except User.DoesNotExist:
            return render_response(
                'Please make sure you phone is correct',
                400
            )

    elif not phone:
        return render_response(
            'Please enter your phone number',
            400
        )
    else:
        user = request.user
    sms_token = SmsToken.objects.filter(user=user).latest('id')
    if sent_token == sms_token.sms_token and sms_token.valid:
        profile = user.profile
        profile.disabled = False
        profile.save()
        sms_token.delete()
        if anonymous:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

        # Fool attacker into thinking that the number is
        # not registered with 201
        return render_response(
            'Successfully logged in' if anonymous
            else 'Phone verified successfully',
            201 if anonymous else 200
        )

    else:
        return render_response(
            'You have entered an incorrect code',
            400
        )


@csrf_exempt
@not_logged_in_required
def user_by_phone(request):
    phone = request.POST.get('phone')
    phone = re.sub(' +', '', phone)
    try:
        validate_international_phonenumber(phone)
    except ValidationError as e:
        context = {
            'status': 'error',
            'msg': str(e.message)
        }
        return HttpResponse(
            json.dumps(context),
            status=400,
            content_type='application/json'
        )

    user, created = User.objects.get_or_create(username=phone)
    Profile.objects.get_or_create(user=user)
    token = SmsToken(user=user)
    token.save()
    res = _send_sms(user, token)
    if isinstance(res, TwilioException):
        return JsonResponse({'status': 'error'})
    else:
        return JsonResponse({'status': 'ok'})


@login_required
def user_address_ajax(request):
    user = request.user
    template = get_template('core/partials/user_address.html')
    addresses = Address.objects.filter(user=user, type="D")
    return HttpResponse(template.render({'addresses': addresses},
                                        request))


@login_required
def create_withdraw_address(request):
    error_message = 'Error creating address: %s'

    address = request.POST.get('value')
    addr = Address()
    addr.type = Address.WITHDRAW
    addr.user = request.user
    addr.address = address

    try:
        validate_bc(addr.address)
        addr.save()
        resp = {'status': 'OK', 'pk': addr.pk}

    except ValidationError:
        resp = {'status': 'ERR', 'msg': 'The supplied address is invalid.'}

    except Exception as e:
        msg = error_message % (e)
        resp = {'status': 'ERR', 'msg': msg}

    return JsonResponse(resp, safe=False)
