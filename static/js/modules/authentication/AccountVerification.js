import Notifier from '../helpers/Notifier.js';
import InputsHelper from '../helpers/InputsHelper.js';

export default class AccountVerification {
    constructor() {
        this.verificationEndpoint = '/en/accounts/verify_user/';
        this.verificationField = $('#verification_code');

        this.initVerifyAccountHandler();
        this.initVerifyAutoSubmit(this);
    }

    initVerifyAutoSubmit(that) {
        this.verificationField.on('keyup', InputsHelper.stripSpaces);
        this.verificationField.on('keyup', function() {
            let val = $(this).val();
            if (val && val.length == $(this).attr('maxlength')) {
                let payload = that.getVerifyAccountPayload();
                that.verifyAccount(payload);
            }
        })
    }

    initVerifyAccountHandler() {
        $('.verify-acc').on('click', () => {
            let payload = this.getVerifyAccountPayload();
            this.verifyAccount(payload);
        });
    }

    getVerifyAccountPayload() {
        let email,
            phone,
            token,
            username,
            login_with_email = true;

        if ($('#email-verification').is(':visible')) {
            email = $('.register #email').val();
            token = $('#verification_code').val();
        } else {
            login_with_email = false;
            if ($('#login-form').is(':visible')) {
                token = $('#id_password').val();
                username = $('#id_username').val();
                if (username.indexOf('@') !== -1) {
                    email = username;
                    login_with_email = true;
                } else {
                    phone = username;
                }
            } else {
                token = $('#verification_code').val();
                phone = $('.register .phone').val();
            }
        }

        return {
            token: token,
            phone: phone,
            email: email,
            login_with_email: login_with_email
        };
    }

    verifyAccount(payload) {
        if ($('#login-form').is(':visible')) {
            $('.login-otp').addClass('disabled');
        }

        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: this.verificationEndpoint,
            data: payload,
            statusCode: {
                201: function(data) {
                    if ($('#login-form').is(':visible')) {
                        window.location.href = '/';
                    } else {
                        let orderObject = require('../orders.js');
                        orderObject.reloadRoleRelatedElements();
                        orderObject.changeState(null, 'next');
                    }
                },
                400: function(data) {
                    if ($('#login-form').is(':visible')) {
                        $('.login-otp').removeClass('disabled');
                    }
                    
                    Notifier.failureResponse(
                        data,
                        'Incorrect code'
                    );
                },
                410: function(data) {
                    if ($('#login-form').is(':visible')) {
                        $('.login-otp').removeClass('disabled');
                    }
                    return Notifier.failureResponse(
                        data,
                        'Your token has expired, please request a new token'
                    );
                },
                403: Notifier.lockoutResponse
            }
        });
    }
}