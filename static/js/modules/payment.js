!(function(window ,$) {
    "use strict";
    var pref = null;
    function loadPaymentMethods(cardsEndpoint, currency) {
        if (!currency || currency.length > 3) {
            return;
        }
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

    function setPaymentPreference(new_pref) {
        pref = new_pref;
    }

    function getPaymentPreference() {
        return pref;
    }

    function loadPaymentMethodsAccount(paymentMethodsAccountEndpoint, pm) {
        if (!pm) {
            return;
        }
        var data = {'payment_method': pm};

        $.post(paymentMethodsAccountEndpoint, data, function (data) {
            $(".paymentMethodsAccount").html($(data));
        });
        $('.paymentMethodsAccount').removeClass('hidden');
    }

    module.exports =
    {
        loadPaymentMethods: loadPaymentMethods,
        loadPaymentMethodsAccount: loadPaymentMethodsAccount,
        setPaymentPreference: setPaymentPreference,
        getPaymentPreference: getPaymentPreference
    };

}(window, window.jQuery)); //jshint ignore:line
