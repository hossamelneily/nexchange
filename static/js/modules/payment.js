!(function(window ,$) {
    "use strict";

    function loadPaymentMethods(cardsEndpoint, currency) {
        var payload = {
            '_locale': $('.topright_selectbox').val(),
            'currency': currency
        };
        $.ajax({
            url: cardsEndpoint,
            type: 'POST',
            data: payload,
            success: function (data) {
                $(".paymentSelectionContainer").html($(data));
            }
        });
    }

    function loadPaymentMethodsAccount(paymentMethodsAccountEndpoint, pm) {
        var data = {'payment_method': pm};

        $.post(paymentMethodsAccountEndpoint, data, function (data) {
            $(".paymentMethodsAccount").html($(data));
        });
        $('.paymentMethodsAccount').removeClass('hidden');
    }

    module.exports =
    {
        loadPaymentMethods: loadPaymentMethods,
        loadPaymentMethodsAccount: loadPaymentMethodsAccount
    };

}(window, window.jQuery)); //jshint ignore:line
