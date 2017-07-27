/*jshint esversion: 6 */

import Clipboard from 'clipboard';
import Notifier from './helpers/Notifier.js';

!(function(window, $) {
    "use strict";
    var orderObject,
        apiRoot = '/en/api/v1',
        createAanonymousEndpoint = '/en/accounts/create_anonymous_user/',
        menuEndpoint = apiRoot + '/menu',
        breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
        validatePhoneEndpoint = '/en/accounts/verify_user/';

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

    function createAnonymousAccount() {
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: createAanonymousEndpoint,
            statusCode: {
                200: function(data) {
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

    function verifyAnonymous() {
        orderObject = require('./orders.js');
        orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
        orderObject.changeState(null, 'next');
    }

    module.exports = {
        canProceedtoRegister: canProceedtoRegister,
        createAnonymousAccount: createAnonymousAccount,
        verifyAnonymous: verifyAnonymous
    };
}(window, window.jQuery)); //jshint ignore:line