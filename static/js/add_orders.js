$(function() {
    // TODO: get api root via DI
    var apiRoot = '/en/api/v1',
        createAccEndpoint = apiRoot + '/phone',
        menuEndpoint = apiRoot + '/menu',
        breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
        validatePhoneEndpoint = '/en/profile/verifyPhone/',
        placerAjaxOrder = '/en/order/ajax/',
        paymentAjax = '/en/payment/ajax/';

    $('.btn-circle').on('click', function () {
        $('.btn-circle.btn-info').removeClass('btn-info').addClass('btn-default');
        $(this).addClass('btn-info').removeClass('btn-default').blur();
    });


    var csrf_token = $('#csrfmiddlewaretoken').val();
    //console.log(csrf_token);

    $('.next-step, .prev-step').on('click', changeState);


    $('.choose-opr').on('click', function () {
        changeState('next');
    });

    $('.create-acc').on('click', function () {
        var regPayload = {
            phone: $('#phone').val()
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
                //$("#phone").attr("disabled", "disabled")
                changeState('next');
            },
            error: function (jqXHR, textStatus, errorThrown) {
                alert('Invalid phone number');
            }
        });
    });

    $('.verify-acc').on('click', function () {
        var verifyPayload = {
            token: $("#verification_code").val(),
            phone: $("#phone").val()
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
        var verifyPayload = {
            "trade-type": $(".trade-type").val(),
            "csrfmiddlewaretoken": $("#csrfmiddlewaretoken").val(),
            "amount-cash": $('.amount-cash').val(),
            "amount-coin": $('.amount-coin').val(),
            "currency_from": $('.currency-from').val(),
            "user_id":$("#user_id").val()
        };
        //console.log(verifyPayload);
        
        $.ajax({
            type: "post",
            url: placerAjaxOrder,
            dataType: 'text',
            data: verifyPayload,
            contentType: 'application/x-www-form-urlencoded; charset=UTF-8',    
            success: function (data) {
                //console.log(data)
                $('.menu4').addClass('hidden');
                $('.successOrder').removeClass('hidden');
                $(".successOrder").html($(data));
                loadPaymenMethods(paymentMethodsEndpoint);
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
    var paneClass = '.tab-pane',
        tab = $('.tab-pane.active'),
        action = action || (this).hasClass('next-step') ? 'next' :'prev',
        nextStateId = tab[action](paneClass).attr('id'),
        nextState = $('[href="#'+ nextStateId +'"]'),
        menuPrefix = "menu",
        numericId = parseInt(nextStateId.replace(menuPrefix, '')),
        currStateId = menuPrefix + (numericId - 1),
        currState =  $('[href="#'+ currStateId +'"]');

    if(nextState.hasClass('disabled') &&
        numericId < $(".process-step").length &&
        numericId > 1) {
        changeState(action);
    }

    setButtonDefaultState(nextStateId);
    currState.addClass('btn-success');
    nextState
        .addClass('btn-info')
        .removeClass('btn-default')
        .tab('show');
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

