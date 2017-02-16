!(function(window, $) {
    "use strict";
    var orderObject = require('./orders.js'),
        apiRoot = '/en/api/v1',
        createAccEndpoint =  '/en/accounts/authenticate/',
        menuEndpoint = apiRoot + '/menu',
        breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
        validatePhoneEndpoint = '/en/accounts/verify_phone/';


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

    function seemlessRegistration (payload) {
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: createAccEndpoint,
            data: payload,
            statusCode: {
                200: function (data) {
                    $('.register .step2').removeClass('hidden');
                    $('.verify-acc').removeClass('hidden');
                    $('.create-acc').addClass('hidden');
                    $('.create-acc.resend').removeClass('hidden');
                },
                400: function (data) {
                    return failureResponse(
                        data,
                        'Invalid phone number'
                    );
                },
                403: lockoutResponse,
                428: function (data) {
                    return failureResponse(
                        data,
                        'Invalid phone number'
                    );
                }
            }
        });
    }

    function verifyAccount (payload) {
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: validatePhoneEndpoint,
            data: payload,
            statusCode: {
                201: function(data) {
                    orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                    orderObject.changeState(null, 'next');
                },
                400: function (data) {
                    failureResponse(
                        data,
                        'Incorrect code'
                    );
                },
                410: function (data) {
                    // deocreatedAuth();
                    return failureResponse(
                        data,
                        'Your token has expired, please request a new token'
                    );
                },
                403: lockoutResponse
            }
        });

    }

    module.exports = {
        canProceedtoRegister: canProceedtoRegister,
        seemlessRegistration: seemlessRegistration,
        verifyAccount: verifyAccount
    };
}(window, window.jQuery)); //jshint ignore:line