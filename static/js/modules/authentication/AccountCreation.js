import register from '../register.js';
import Notifier from '../helpers/Notifier.js';
import RegexChecker from '../helpers/RegexChecker.js';
import AccountVerification from './AccountVerification.js';

export default class AccountCreation {
    constructor() {
        this.createAccEndpoint = '/en/accounts/authenticate/';

        this.initCreateAccButtonHandler();
        this.initEmailOrSmsInput();
    }

    initCreateAccButtonHandler() {
        $('.create-acc').on('click', (event) => {
            if ($(event.currentTarget).hasClass('disabled')) return;

            $('.user-anonymous').addClass('hidden');

            if ($('.send-otp').is(':visible') || $('.send').is(':visible')) {
                grecaptcha.execute();
            } else {
                window.submitCreateAcc();
            }
        });
    }

    initEmailOrSmsInput() {
        $('#email, #phone').on('change paste keyup', function() {
            let val = $(this).val();

            if (val.length) {
                $('.create-acc').not('.resend').removeClass('disabled');

                if (RegexChecker.isPhone(val) && !$('#phone-verification').is(":visible")) {
                    $('#phone-verification').removeClass('hidden').find('input').val(val).focus();
                    $(this).val('').parent().addClass('hidden');
                }
            } else {
                $('.create-acc').not('.resend').addClass('disabled');
                $('#phone-verification').addClass('hidden');
                $('#email-verification').removeClass('hidden').find('input').focus();
            }
        });
    }

    seamlessRegistration(payload, callback) {
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: this.createAccEndpoint,
            data: payload,
            statusCode: {
                200: function(data) {
                    if ($('#login-form').is(':visible')) {
                        $('.login-otp').removeClass('hidden');
                        $('.resend-otp').removeClass('hidden');
                        let submit = $('#submit_auth'),
                            password = $('#id_password');
                        submit.addClass('hidden');
                        submit.addClass('disabled');
                        password.val('');
                        password.attr('placeholder', gettext('SMS Token'));
                        password.attr('type', 'text');
                        $('label[for="id_password"]').text(
                            gettext('One Time Password')
                        );
                        $('.send-otp').addClass('hidden');
                        $('#id_username').attr('readonly', true);
                    } else {
                        // This part is used in registration during
                        // the order process.
                        $('.register .step2').removeClass('hidden');
                        $('.verify-acc').removeClass('hidden');
                        $('.create-acc').addClass('hidden');
                        $('.create-acc.resend').removeClass('hidden');
                        $('#verification_code').prop('disabled', false);
                    }                    
                    
                },
                400: function(data) {
                    return Notifier.failureResponse(
                        data,
                        gettext('Invalid phone number or email address')
                    );
                },
                503: function(data) {
                    return Notifier.failureResponse(
                        data,
                        gettext('Service provider error')
                    );
                },
                403: Notifier.lockoutResponse,
                428: function(data) {
                    return Notifier.failureResponse(
                        data,
                        gettext('Invalid phone number or email address')
                    );
                }
            }
        });
    }
}

window.submitCreateAcc = () => {
    let email = null,
        phone = null,
        login_with_email = true;

    if ($('#email').is(":visible")) {
        email = $('#email').val();
    } else {
        login_with_email = false;

        if ($('#login-form').is(':visible')) {
            let username = $('#id_username').val();
            if (username.indexOf('@') !== -1) {
                email = username;
                login_with_email = true;
            } else {
                phone = username;
            }
        } else {
            phone = $('#phone').val();
        }
    }
    let regPayload = {
        phone: phone,
        email: email,
        login_with_email: login_with_email,
        g_recaptcha_response: grecaptcha.getResponse()
    };

    let accountCreation = new AccountCreation();
    accountCreation.seamlessRegistration(regPayload);
};