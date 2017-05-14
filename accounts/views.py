import json

from axes.decorators import watch_login
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from phonenumber_field.validators import validate_international_phonenumber
from nexchange.utils import sanitize_number
from django.forms import modelformset_factory


from accounts.decoratos import not_logged_in_required, recaptcha_required
from accounts.forms import (CustomUserCreationForm, UpdateUserProfileForm,
                            UserForm, UserProfileForm)
from referrals.models import ReferralCode
from accounts.models import NexchangeUser as User
from accounts.models import Profile, SmsToken
from orders.models import Order
from core.models import Address
from core.validators import (validate_address, validate_btc, validate_ltc,
                             validate_eth)
from django.core.validators import validate_email
from referrals.forms import ReferralTokenForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from accounts.api_clients.auth_messages import AuthMessages

auth_msg_api = AuthMessages()
send_auth_sms = auth_msg_api.send_auth_sms
send_auth_email = auth_msg_api.send_auth_email


def user_registration(request):
    template = 'accounts/user_registration.html'
    success_message = _(
        'Registration completed. Check your phone '
        'for SMS confirmation code.')
    error_message = _('Error during accounts. <br>Details: {}')

    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic(using='default'):
                    user = user_form.save(commit=False)
                    user.username = str(profile_form.cleaned_data['phone'])
                    user.save()

                    profile_form = UserProfileForm(
                        request.POST, instance=user.profile)
                    profile = profile_form.save(commit=False)
                    profile.disabled = True
                    profile.save()
                    send_auth_sms(user)

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
    ReferralFormSet = modelformset_factory(ReferralCode,
                                           form=ReferralTokenForm, extra=1)

    def get(self, request):
        user_form = UserForm(
            instance=self.request.user)
        profile_form = UpdateUserProfileForm(
            instance=self.request.user.profile)
        all_referrals = request.user.referral_code.all()
        referral_formset = \
            UserUpdateView.ReferralFormSet(queryset=all_referrals)

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'referral_formset': referral_formset,
        }

        return render(request, 'accounts/user_profile.html', context)

    def post(self, request):
        user_form = \
            UserForm(request.POST,
                     instance=self.request.user)
        profile_form = \
            UpdateUserProfileForm(request.POST,
                                  instance=self.request.user.profile)
        referral_formset = UserUpdateView.ReferralFormSet(request.POST)

        success_message = ''

        # TODO: separate referrals and profile in Views.py and Frontend (tabs)
        if user_form.is_valid() and \
                profile_form.is_valid():
            success_message += '{}\n'.format(_('Profile updated successfully'))
            user_form.save()
            profile_form.save()

        if referral_formset.is_valid():
            instances = referral_formset.save(commit=False)
            for instance in instances:
                success_message += _('Referral codes updated successfully')
                instance.user = request.user.pk
                instance.save()

        if success_message:
            messages.success(self.request, success_message)
            return redirect(reverse('accounts.user_profile'))
        else:
            ctx = {
                'user_form': user_form,
                'profile_form': profile_form,
                'referral_formset': referral_formset
            }

            return render(request, 'accounts/user_profile.html', ctx, )


@watch_login
def resend_sms(request):
    """Thi is used solely in profile page"""
    phone = request.POST.get('phone')
    if request.user.is_anonymous() and phone:
        user = User.objects.get(profile__phone=phone)
    else:
        user = request.user
    message = send_auth_sms(user)
    return JsonResponse({'message_sid': message.sid}, safe=False)


@watch_login
def verify_user(request):
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
    sent_token = sanitize_number(sent_token)
    login_with_email = request.POST.get('login_with_email', False) == 'true'
    email = request.POST.get('email', '')
    phone = request.POST.get('phone', '')
    phone = sanitize_number(phone, True)
    if login_with_email:
        username = email
        _type = 'email'
    else:
        username = phone
        _type = 'phone'
    anonymous = request.user.is_anonymous()
    if anonymous and username:
        # fast registration
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return render_response(
                'Please make sure your {} is correct'.format(_type),
                400
            )

    elif anonymous and not username:
        # Fast registration
        return render_response(
            'Please enter your {}'.format(_type),
            400
        )
    else:
        # Profile page
        user = request.user

    try:
        sms_token = SmsToken.objects.filter(user=user).latest('id')
    except SmsToken.DoesNotExist:
        return render_response(
            'Your token has expired, '
            'Please request a new token',
            400
        )
    if sent_token == sms_token.sms_token:
        if not sms_token.valid:
            return render_response(
                'Your token has expired, '
                'Please request a new token',
                410
            )
        profile = user.profile
        if not login_with_email:
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
            else '{} verified successfully'.format(_type),
            201 if anonymous else 200
        )

    else:
        return render_response(
            'You have entered an incorrect code',
            400
        )


@csrf_exempt
@recaptcha_required
@not_logged_in_required
@watch_login
def user_get_or_create(request):
    """This is used for seemless fast login"""
    login_with_email = request.POST.get('login_with_email', False) == 'true'
    phone = request.POST.get('phone', '')
    phone = sanitize_number(phone, True)
    email = request.POST.get('email', '')
    user_data = {}
    profile_data = {}
    if not login_with_email:
        username = profile_data['phone'] = phone
        _validator = validate_international_phonenumber
    else:
        username = user_data['email'] = email
        _validator = validate_email
    try:
        _validator(username)
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
    user_data['username'] = username

    user, u_created = User.objects.get_or_create(**user_data)
    if u_created:
        profile_data['disabled'] = True
    profile_data['user'] = user
    Profile.objects.get_or_create(**profile_data)

    if not login_with_email:
        res = send_auth_sms(user)
    else:
        res = send_auth_email(user)
    if isinstance(res, Exception):
        return JsonResponse({'status': 'error'})
    else:
        return JsonResponse({'status': 'ok'})


@login_required
def user_address_ajax(request):
    user = request.user
    template = get_template('core/partials/select_widget.html')
    addresses = Address.objects.filter(user=user, type="D")
    return HttpResponse(template.render({'addresses': addresses},
                                        request))


@login_required
def create_withdraw_address(request, order_pk):
    error_message = 'Error creating address: %s'
    order = Order.objects.get(pk=order_pk)
    if not order.user.profile.is_verified and not order.exchange:
        pm = order.payment_preference.payment_method
        if pm.required_verification_buy:
            resp = {
                'status': 'ERR',
                'msg': 'You need to be a verified user to set withdrawal '
                       'address for order with payment method \'{}\''
                       ''.format(pm.name)
            }
            return JsonResponse(resp, safe=False)

    address = request.POST.get('value')
    addr = Address()
    addr.type = Address.WITHDRAW
    addr.user = request.user
    addr.address = address
    if order.order_type == Order.BUY:
        currency = order.pair.base
    else:
        currency = order.pair.quote
    addr.currency = currency

    try:
        if currency.code == 'BTC':
            validate_btc(addr.address)
        elif currency.code == 'LTC':
            validate_ltc(addr.address)
        elif currency.code == 'ETH':
            validate_eth(addr.address)
        else:
            validate_address(addr.address)
        addr.save()
        resp = {'status': 'OK', 'pk': addr.pk}

    except ValidationError:
        resp = {'status': 'ERR', 'msg': 'The supplied address is invalid.'}

    except Exception as e:
        msg = error_message % (e)
        resp = {'status': 'ERR', 'msg': msg}

    return JsonResponse(resp, safe=False)


def change_password(request):
    main_form = PasswordChangeForm
    if request.user.password == '':
        main_form = SetPasswordForm
    if request.method == 'POST':
        form = main_form(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(
                request, _('Your password was successfully updated!')
            )
            redirect_url = reverse('accounts.login')
            return redirect(redirect_url)
        else:
            messages.error(
                request, _('Please correct the error below.')
            )
    else:
        form = main_form(request.user)
    return render(request, 'accounts/change_password.html', {
        'form': form
    })
