!(function(window ,$) {
    "use strict";

    function loadPaymenMethods(paymentMethodsEndpoint) {
        $.get(paymentMethodsEndpoint, function (data) {
            $(".paymentMethods").html($(data));
        });
        $('.paymentMethods').removeClass('hidden');
    }

    function loadPaymenMethodsAccount(paymentMethodsAccountEndpoint, pm) {
        var data = {'payment_method': pm};

        $.get(paymentMethodsAccountEndpoint, data, function (data) {
            $(".paymentMethodsAccount").html($(data));
        });
        $('.paymentMethodsAccount').removeClass('hidden');
    }

    function paymentNegotiation () {

            $('.supporetd_payment').addClass('hidden');
            var elem = $(this),
            paymentType = elem.data('type'),
            preferenceIdentifier = elem.data('identifier');
            $('.payment-preference-confirm').text(paymentType);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);
            // $('#PayMethModal').modal('toggle');
            $('.payment-method').val(paymentType);
            orderObject.changeState(null, 'next');
            $('.footerpay').addClass('hidden');
            $('.buy-go').removeClass('hidden');
            $('.sell-go').addClass('hidden');
            window.action = window.ACTION_BUY;
            $('.next-step')
                .removeClass('btn-info')
                .removeClass('btn-danger')
                .addClass('btn-success');
        }

    module.exports =
    {
        loadPaymenMethods: loadPaymenMethods,
        loadPaymenMethodsAccount: loadPaymenMethodsAccount
    };

}(window, window.jQuery)); //jshint ignore:line
