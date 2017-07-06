/*jshint esversion: 6 */

import Clipboard from 'clipboard';

!(function(window, $) {
    "use strict";
    var orderObject,
        apiRoot = '/en/api/v1',
        createAccEndpoint =  '/en/accounts/authenticate/',
        createAanonymousEndpoint =  '/en/accounts/create_anonymous_user/',
        menuEndpoint = apiRoot + '/menu',
        breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
        validatePhoneEndpoint = '/en/accounts/verify_user/';


    function lockoutResponse (data) {
        toastr.error(window.getLockOutText(data));
    }

    function failureResponse (data, defaultMsg) {
        var _defaultMsg = gettext(defaultMsg),
            message = data.responseJSON.message || _defaultMsg;
        toastr.error(message);

    }

    function canProceedtoRegister(objectName) {
        var payMeth = $('#payment_method_id').val(),
            userAcc = $('#user_address_id').val(),
            userAccId = $('#new_user_account').val();
        if (!((objectName == 'menu2' || objectName == 'btn-register') &&
            payMeth === '' &&
            userAcc === '' &&
            userAccId === '')) {
            return true;
        }
        return false;
    }

    function createAnonymousAccount () {
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: createAanonymousEndpoint,
            statusCode: {
                200: function (data) {
                    $('.register .step2').removeClass('hidden');
                    $('.create-anonymous-acc').addClass('hidden');
                    $('.user-authenticated').addClass('hidden');
                    $('.verify-anonymous').removeClass('hidden');
                    $('.copy-key').removeClass('hidden');
                    $('.hide-key').removeClass('hidden');
                    $('#user-login-key').val(data.key);
                    new Clipboard('.copy-key');
                }
            }
        });
    }

    function seemlessRegistration (payload) {
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: createAccEndpoint,
            data: payload,
            statusCode: {
                200: function (data) {
                    if ($('#login-form').is(':visible')) {
                        $('.login-otp').removeClass('hidden');
                        $('.resend-otp').removeClass('hidden');
                        var submit = $('#submit_auth'),
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
                        $('.register .step2').removeClass('hidden');
                        $('.verify-acc').removeClass('hidden');
                        $('.create-acc').addClass('hidden');
                        $('.create-acc.resend').removeClass('hidden');
                    }
                },
                400: function (data) {
                    return failureResponse(
                        data,
                        gettext('Invalid phone number')
                    );
                },
                503: function (data) {
                    return failureResponse(
                        data,
                        gettext('Service provider error')
                    );
                },
                403: lockoutResponse,
                428: function (data) {
                    return failureResponse(
                        data,
                        gettext('Invalid phone number')
                    );
                }
            }
        });
    }

    function verifyAccount (payload) {
        if ($('#login-form').is(':visible')) {
            $('.login-otp').addClass('disabled');
        }
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: validatePhoneEndpoint,
            data: payload,
            statusCode: {
                201: function(data) {
                    if ($('#login-form').is(':visible')) {
                        window.location.href = '/';
                    } else {
                        orderObject = require('./orders.js');
                        orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                        orderObject.changeState(null, 'next');
                    }
                },
                400: function (data) {
                    if ($('#login-form').is(':visible')) {
                        $('.login-otp').removeClass('disabled');
                    }
                    failureResponse(
                        data,
                        'Incorrect code'
                    );
                },
                410: function (data) {
                    if ($('#login-form').is(':visible')) {
                        $('.login-otp').removeClass('disabled');
                    }
                    return failureResponse(
                        data,
                        'Your token has expired, please request a new token'
                    );
                },
                403: lockoutResponse
            }
        });

    }

    function verifyAnonymous () {
        orderObject = require('./orders.js');
        orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
        orderObject.changeState(null, 'next');
    }

    module.exports = {
        canProceedtoRegister: canProceedtoRegister,
        seemlessRegistration: seemlessRegistration,
        createAnonymousAccount: createAnonymousAccount,
        verifyAccount: verifyAccount,
        verifyAnonymous: verifyAnonymous
    };
}(window, window.jQuery)); //jshint ignore:line