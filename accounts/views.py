from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from accounts.forms import CustomUserCreationForm, UserProfileForm,\
    UpdateUserProfileForm, UserForm
from referrals.forms import ReferralTokenForm
from django.db import transaction
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.decorators import method_decorator
from twilio.exceptions import TwilioException
from twilio.rest import TwilioRestClient
from django.views.generic import View
from accounts.models import SmsToken
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.http import JsonResponse
from django.template.loader import get_template
from core.models import Address
from accounts.models import Profile
from django.contrib.auth.models import User
from core.validators import validate_bc
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt


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
            'referral_form': referral_form
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
    sent_token = request.POST.get('token')
    phone = request.POST.get('phone')
    anonymous = request.user.is_anonymous()
    if anonymous and phone:
        user = User.objects.get(username=phone)
    else:
        user = request.user
    sms_token = SmsToken.objects.filter(user=user).latest('id')
    if sent_token == sms_token.sms_token and sms_token.valid:
        profile = user.profile
        profile.disabled = False
        profile.save()
        status = 'OK'
        sms_token.delete()
        if anonymous:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

    else:
        status = 'NO_MATCH'

    return JsonResponse({'status': status}, safe=False)


@csrf_exempt
def user_by_phone(request):
    phone = request.POST.get('phone')
    user, created = User.objects.get_or_create(username=phone)
    Profile.objects.get_or_create(user=user)
    token = SmsToken(user=user)
    token.save()
    res = _send_sms(user, token)
    if isinstance(res, TwilioException):
        return JsonResponse({'status': 'error'})
    else:
        return JsonResponse({'status': 'ok'})


@login_required()
def user_address_ajax(request):
    user = request.user
    template = get_template('core/partials/user_address.html')
    addresses = Address.objects.filter(user=user, type="D")
    return HttpResponse(template.render({'addresses': addresses},
                                        request))


@login_required()
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
