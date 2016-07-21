$(function() {
    // TODO: get api root via DI
    $('#payment_method_id').val("");
    $('#user_address_id').val("");
    $('#new_user_account').val("");
    var apiRoot = '/en/api/v1',
        createAccEndpoint = apiRoot + '/phone',
        menuEndpoint = apiRoot + '/menu',
        breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
        validatePhoneEndpoint = '/en/profile/verifyPhone/',
        placerAjaxOrder = '/en/order/ajax/',
        paymentAjax = '/en/payment/ajax/',
        getBtcAddress = '/en/kraken/genAddress/';

    $('.next-step, .prev-step').on('click', changeState);

    $('.create-acc').on('click', function () {
        var regPayload = {
            // TODO: check collision with qiwi wallet
            phone: $('.register .phone').val()
        };
        $.ajax({
            type: "POST",
            url: createAccEndpoint,
            data: regPayload,
            success: function (data) {
                $('.register .step2').removeClass('hidden');
                $('.verify-acc').removeClass('hidden');
                $(".create-acc").addClass('hidden');
                $(".create-acc.resend").removeClass('hidden');
            },
            error: function (jqXHR, textStatus, errorThrown) {
                alert('Invalid phone number');
            }
        });
    });

    $('.verify-acc').on('click', function () {
        var verifyPayload = {
            token: $('#verification_code').val(),
            phone: $('.register .phone').val()
        };
        $.ajax({
            type: "POST",
            url: validatePhoneEndpoint,
            data: verifyPayload,
            success: function (data) {
                if (data.status === 'OK') {
                    reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                    changeState('next');
                } else {
                    window.alert("The code you sent was incorrect. Please, try again.")
                }
            },
            error: function () {
                window.alert("Something went wrong. Please, try again.")
            }
        });

    });
    

    $('.place-order').on('click', function () {
        //TODO verify if $(this).hasClass('sell-go') add 
        // the othre type of transaction
        
        var verifyPayload = {
                "trade-type": $(".trade-type").val(),
                "csrfmiddlewaretoken": $("#csrfmiddlewaretoken").val(),
                "amount-coin": $('.amount-coin').val(),
                "currency_from": $('.currency-from').val(), //fiat
                "currency_to": $('.currency-to').val(), //crypto
                "pp_type": $(".payment-method"),
                "pp_identifier": $(".payment-preference-identifier"),
                "pp_owner": $(".payment-preference-owner")
            };
            
        $.ajax({
            type: "post",
            url: placerAjaxOrder,
            dataType: 'text',
            data: verifyPayload,
            contentType: 'application/x-www-form-urlencoded; charset=UTF-8',    
            success: function (data) {
                //console.log(data)
                //if the transaction is Buy
                if (window.action == 1){ 
                    $('.step-confirm').addClass('hidden');
                    //$('.successOrder').removeClass('hidden');
                    $(".successOrder").html($(data));
                    $("#orderSuccessModal").modal({backdrop: "static"});
                }
                //if the transaction is Sell
                else{
                    $('.step-confirm').addClass('hidden');
                    $('#btcAddress').text(data['address']);
                    $("#orderSuccessModalSell").modal({backdrop: "static"});
                }

            },
            error: function () {
                window.alert("Something went wrong. Please, try again.")
            }
        });

    });

  $('.make-payment').on('click', function () {
        var verifyPayload = {
            "order_id": $(".trade-type").val(),
            "csrfmiddlewaretoken": $("#csrfmiddlewaretoken").val(),
            "amount-cash": $('.amount-cash').val(),
            "currency_from": $('.currency-from').val(),
            "user_id":$("#user_id").val()
        };
        //console.log(verifyPayload);
        
        $.ajax({
            type: "post",
            url: paymentAjax,
            dataType: 'text',
            data: verifyPayload,
            contentType: 'application/x-www-form-urlencoded; charset=UTF-8',    
            success: function (data) {
                //console.log(data)
                $('.paymentMethodsHead').addClass('hidden');
                $('.paymentMethods').addClass('hidden');
                $('.paymentSuccess').removeClass('hidden');
                $(".paymentSuccess").html($(data));
                changeState('next');
                
               // loadPaymenMethods(paymentMethodsEndpoint);
                
            },
            error: function () {
                window.alert("Something went wrong. Please, try again.")
            }
        });

    });

    $('.buy .payment-type-trigger').on('click', function () {
        var paymentType = $(this).data('type');
        $("#PayMethModal").modal('toggle');
        $(".payment-method").val(paymentType);
    });

    $('.sell .payment-type-trigger').on('click', function () {
        var paymentType = $(this).data('type');
        $("#UserAccountModal").modal('toggle');
        if (paymentType === 'c2c') {
            $("#CardSellModal").modal('toggle');
        } else if(paymentType === 'qiwi') {
            $("#QiwiSellModal").modal('toggle');
        }
        else {
            $(".payment-method").val(paymentType);
        }
    });

    $('.sellMethModal .back').click(function () {
        $(this).closest('.modal').modal('toggle');
        $("#UserAccountModal").modal('toggle');
    });

    $('.payment-widget .val').on('keyup', function() {
        var val = $(this).closest('.val');
        if (!val.val().length) {
           $(this).removeClass('error').removeClass('valid');
            return;
        }
       if (val.hasClass('jp-card-invalid')) {
            $(this).removeClass('valid').addClass('error');
            $('.save-card').addClass('disabled');
        } else {
           $(this).removeClass('error').addClass('valid');
           $('.save-card').removeClass('disabled');
       }

    });

    $('.payment-widget .save-card').on('click', function () {
        // TODO: Add handling for qiwi wallet with .intlTelInput("getNumber")
        if ($(this).hasClass('disabled')) {
            return false;
        }
        var preferenceIdentifier = $(this).find('.val').val(),
            preferenceOwner = $(this).find('.name').val();

        $(".payment-preference-owner").val(preferenceOwner);
        $(".payment-preference-identifier").val(preferenceIdentifier);

        $(this).closest('.modal').modal('dismiss').delay(500).queue( function (next){
            changeState("next");
            next();
        });
    });
});

function setButtonDefaultState (tabId) {
    if (tabId === 'menu2') {
        var modifier = action === ACTION_SELL ? 'btn-danger' : 'btn-success';
        $('.next-step').removeClass('btn-info').addClass(modifier);
    } else {
        $('.next-step').removeClass('btn-success').removeClass('btn-danger').addClass('btn-info');
    }
    $('.btn-circle.btn-info')
        .removeClass('btn-info')
        .addClass('btn-default');
}

function changeState (action) {
    if($(this).hasClass('disabled')) {
        //todo: allow user to buy placeholder value or block 'next'?
        return;
    }

    var paneClass = '.tab-pane',
        tab = $('.tab-pane.active'),
        action = action || (this).hasClass('next-step') ? 'next' :'prev',
        nextStateId = tab[action](paneClass).attr('id'),
        nextState = $('[href="#'+ nextStateId +'"]'),
        menuPrefix = "menu",
        numericId = parseInt(nextStateId.replace(menuPrefix, '')),
        currStateId = menuPrefix + (numericId - 1),
        currState =  $('[href="#'+ currStateId +'"]');

    //skip disabled state, check if at the end
    if(nextState.hasClass('disabled') &&
        numericId < $(".process-step").length &&
        numericId > 1) {
        changeState(action);
    }

    if ( !canProceedtoRegister(currStateId) ){
        $('.trigger-buy').trigger('click', true);
    } else {
        setButtonDefaultState(nextStateId);
        currState.addClass('btn-success');
        nextState
            .addClass('btn-info')
            .removeClass('btn-default')
            .tab('show');
    }

    $(window).trigger('resize');
}

function reloadRoleRelatedElements (menuEndpoint, breadCrumbEndpoint) {
    $.get(menuEndpoint, function (menu) {
        $(".menuContainer").html($(menu));
    });

    $(".process-step .btn")
        .removeClass('btn-info')
        .removeClass('disabled')
        .removeClass('disableClick')
        .addClass('btn-default');
    $(".step4 .btn").addClass('btn-info');
    // Todo: is this required?
    $(".step3 .btn")
        .addClass('disableClick')
        .addClass('disabled');
}

function canProceedtoRegister(objectName){
    var payMeth = $('#payment_method_id').val(),
    userAcc = $('#user_address_id').val(),
    userAccId = $('#new_user_account').val();
    if (!((objectName == 'menu2' || objectName == 'btn-register') && payMeth == ''
        && userAcc == '' && userAccId == '')) {
            return true;
    }
    return false;
}

//Ugly hack to call from main.js
window.changeState = changeState;
