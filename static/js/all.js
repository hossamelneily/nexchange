(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
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
        getBtcAddress = '/en/kraken/genAddress/',
        DEFAULT_AMOUNT = 1;

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
                "amount-coin": $('.amount-coin').val() || DEFAULT_AMOUNT,
                "currency_from": $('.currency-from').val(), //fiat
                "currency_to": $('.currency-to').val(), //crypto
                "pp_type": $(".payment-method").val(),
                "pp_identifier": $(".payment-preference-identifier").val(),
                "pp_owner": $(".payment-preference-owner").val()
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

},{}],2:[function(require,module,exports){
// using jQuery
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

},{}],3:[function(require,module,exports){
!(function (window, $) {
    $(window).bind("load", function () {
        var footerHeight = 0,
            footerTop = 0,
            $footer = $("footer");

        positionFooter();

        function positionFooter() {
            footerHeight = $footer.height();
            footerTop = ($(window).scrollTop() + $(window).height() - footerHeight) + "px";

            if (($(document.body).height() + footerHeight) < $(window).height()) {
                $footer.css({
                    position: "absolute"
                }).animate({
                    top: footerTop
                })
            } else {
                $footer.css({
                    position: "static"
                })
            }

        }

        $(window)
            .scroll(positionFooter)
            .resize(positionFooter)

    });
}(window, window.jQuery));
},{}],4:[function(require,module,exports){
$(document).ready(function() {

    function withdraw_address_error(msg) {
        $(".withdraw_address_err:visible").html(msg);
    }


    $('[data-toggle="popover"]').on('inserted.bs.popover', function () {

        var span = $(this);
        var popover = $(this).data("bs.popover");
        var forms = popover.tip().find("form");

        var form_update = forms.first();
        var form_create = forms.last();

        var select_addresses = form_update.find("select:first");
        var input_address = form_create.find("input[type=text]:first");
        var btnSetAddress = form_update.find("button[type=submit]:first");        


        var close_popover = function() {
            span.trigger("click");
        };

        var toggle_forms = function() {
            $(".set_withdraw_address").toggle();
            $(".create_withdraw_address").toggle();
        };

        // Links that closes the popover
        $(".closepopover").click(close_popover);

        // Buttons to toggle between select/add address
        $(".toggle_widthdraw_address_form").click(toggle_forms);

        // Copy options from the template object
        // (it may have changed duo to new addresses beend added)
        var options = $("#popover-template select:first > option").clone();
        select_addresses.empty().append(options);

        // if there is one address set for this order, select it
        select_addresses.children("option").each(function(index, option){
            if ( $.trim($(option).text()) === $.trim(span.html()) ) {
                select_addresses.prop('selectedIndex', index);
            }
        })
        
        /**
         * The form which handles 'select one of the existing addresses'
         */
        form_update.submit(function(event) {       
            event.preventDefault();
            withdraw_address_error(''); // clean up

            var selected = select_addresses.find("option:selected").first();            
            if (selected.val() === "") {
                withdraw_address_error("You must select an address first.");
                return false;
            }

            btnSetAddress.button('loading');

            $.post( span.data('url-update'), {'value': selected.val()}, function( data ) {
                if (data.status === 'OK') {
                    span.html(selected.text());
                    span.trigger("click");
                } else {
                    withdraw_address_error(UNKNOW_ERROR);
                }

                btnSetAddress.button('reset');
            }).fail(function(jqXHR){
                if (jqXHR.status == 403) {
                    withdraw_address_error(jqXHR.responseText);
                } else if(data.status === 'ERR') {
                    withdraw_address_error(data.msg);
                } else {
                    withdraw_address_error(UNKNOW_ERROR);
                }
                btnSetAddress.button('reset');
            });
        });

        /**
         * The form which handles 'add a new address'
         */
        form_create.submit(function(event) {            
            event.preventDefault();
            withdraw_address_error(''); // clean up
            
            if (input_address.val() === "") {
                withdraw_address_error("You must insert an address first.");
                return false;
            }

            var btn = form_create.find("button[type=submit]:first");
            btn.button('loading');

            $.post( span.data('url-create'), {'value': input_address.val()}, function( data ) {
                if (data.status === 'OK') {

                    // Add this address as an option to the select
                    select_addresses
                        .append($("<option></option>")
                        .attr("value", data.pk)
                        .text(input_address.val()));
                    select_addresses.val(data.pk);  // select it

                    // updates the template element
                    $("#popover-template select:first")
                        .append($("<option></option>")
                        .attr("value", data.pk)
                        .text(input_address.val()));

                    // clean up the input
                    input_address.val('');  

                    // get back to select form and submit it
                    form_create.find(".toggle_widthdraw_address_form:first").trigger("click");
                    btnSetAddress.trigger("click");

                } else if(data.status === 'ERR') {
                    withdraw_address_error(data.msg);
                } else {
                    withdraw_address_error(UNKNOW_ERROR);
                }

                btn.button('reset');
            }).fail(function(jqXHR){
                if (jqXHR.status == 403) {
                    withdraw_address_error(jqXHR.responseText);
                } else {
                    withdraw_address_error(UNKNOW_ERROR);
                }
                btn.button('reset');
            });
        });


        // Defines wich form will show up when popover opens
        if ( options.length > 1 ) {
            popover.tip().find(".set_withdraw_address:first").toggle();
            popover.tip().find(".cancel_btn").click(toggle_forms);
        } else {
            popover.tip().find(".create_withdraw_address:first").toggle();
            popover.tip().find(".cancel_btn").click(close_popover);
        }
    })

    /**
     * Handles the payment confirmation
     */
    $('.checkbox-inline input').change(function() {
        var pk = $(this).data('pk');
        var spin = $("#spin_confirming_" + pk );
        var container = $(this).closest('.checkbox-inline');
        var toggle = this;
        var withdraw_address = $(".withdraw_address[data-pk=" + pk + "]"); // withdraw_address for this orders

        var treatError = function(msg) {
            // Sets the toggle back and notifies the user about the error
            if ( $(toggle).prop('checked') ){
                $(toggle).data('bs.toggle').off(true);
            } else {
                $(toggle).data('bs.toggle').on(true);
            }

            $(spin).hide();
            $(container).show();

            window.alert(msg);
        };

        $.post( $(this).data('url'), {'paid': $(this).prop('checked')}, function( data ) {

            if (data.status === 'OK') {
                
                
                if (data.frozen) {
                    // so user wont change any payment confirmation
                    $(toggle).bootstrapToggle('disable');

                    // so user cannot edit withdraw_address
                    $("#td-frozen-withdraw-" + pk + " .frozen").html($(withdraw_address).html())
                    $("#td-withdraw-" + pk).hide();                     
                    $("#td-frozen-withdraw-" + pk).show();
                } 

                $(spin).hide();
                $(container).show();
                
            } else {
                treatError(UNKNOW_ERROR);
            }

        }).fail(function(jqXHR){
            if (jqXHR.status == 403) {
                treatError(jqXHR.responseText);
            } else {
                treatError(UNKNOW_ERROR);
            }
        });
        
    });

});


},{}],5:[function(require,module,exports){
!(function (window, $) {
    var apiRoot = '/en/api/v1',
        tickerHistoryUrl = apiRoot +'/price/history',
        tickerLatestUrl = apiRoot + '/price/latest',
        currency = 'rub',
        animationDelay = 3000,
        chartDataRaw,
        paymentMethodsEndpoint = '/en/paymentmethods/ajax/',
        paymentMethodsAccountEndpoint = '/en/paymentmethods/account/ajax/';

    $(".trade-type").val("1");
    window.ACTION_BUY = 1;
    window.ACTION_SELL = 0;
    window.action = ACTION_BUY; // 1 - BUY 0 - SELL


    $(function () {
            setCurrency();
            var timer = null,
                delay = 500,
                phones = $(".phone");

            phones.each(function (idx) {
                if(typeof $(this).intlTelInput === 'function') {
                    // with AMD move to https://codepen.io/jackocnr/pen/RNVwPo
                    $(this).intlTelInput();
                }
            });
            updateOrder($('.amount-coin'), true);
            
            $('.trigger').click( function(event, isNext){
                $('.trigger').removeClass('active');
                $(this).addClass('active');
                if ($(this).hasClass('trigger-buy')) {
                    $('.buy-go').removeClass('hidden');
                    $('.sell-go').addClass('hidden');
                    window.action = window.ACTION_BUY;
                    $('.next-step')
                        .removeClass('btn-info')
                        .removeClass('btn-danger')
                        .addClass('btn-success');
                    $('.step4 i').removeClass('fa-money').addClass('fa-btc');
                    loadPaymenMethods(paymentMethodsEndpoint);
                    $("#PayMethModal").modal({backdrop: "static"});
                } else {
                    $('.buy-go').addClass('hidden');
                    $('.sell-go').removeClass('hidden');
                    window.action = window.ACTION_SELL;
                    $('.next-step')
                        .removeClass('btn-info')
                        .removeClass('btn-success')
                        .addClass('btn-danger');
                    $('.step4 i').removeClass('fa-btc').addClass('fa-money');

                    $("#card-form").card({
                        container: '.card-wrapper',
                        width: 200,
                        placeholders: {
                            number: '•••• •••• •••• ••••',
                            name: 'Ivan Ivanov',
                            expiry: '••/••',
                            cvc: '•••'
                        }
                    });
                    $("#UserAccountModal").modal({backdrop: "static"});


                }

                $(".trade-type").val(window.action);

                updateOrder($('.amount-coin'));

                var newCashClass = action === window.ACTION_BUY ? 'rate-buy' : 'rate-sell';
                $('.amount-cash, .amount-coin')
                    .removeClass('rate-buy')
                    .removeClass('rate-sell')
                    .addClass(newCashClass);
            });

            $('.amount').on('keyup', function () {
                var self = this;
                if (timer) {
                    clearTimeout(timer);
                    timer = null;
                }
                timer = setTimeout(function () {
                    updateOrder($(self));
                }, delay);
            });

             $('.payment-method').on('change', function () {
                loadPaymenMethodsAccount(paymentMethodsAccountEndpoint);

            });

            $('.currency-select').on('change', function () {
                currency = $(this).val().toLowerCase();
                setCurrency($(this));
                //bind all select boxes
                $('.currency-select').not('.currency-to').val($(this).val());
                updateOrder($('.amount-coin'));
            });
            //using this form because the object is inside a modal screen
            $(document).on('change','.payment-method', function () {
                var pm = $('.payment-method option:selected').val();
                $('#payment_method_id').val(pm);
                loadPaymenMethodsAccount(paymentMethodsAccountEndpoint, pm);

            });

        });

    function responseToChart(data) {
        var i,
            resRub = [],
            resUsd = [],
            resEur = [];

        for (i = 0; i < data.length; i+=2) {
            var sell = data[i],
            buy = data[i + 1];
            resRub.push([Date.parse(sell['created_on']), buy['price_rub_formatted'], sell['price_rub_formatted']]);
            resUsd.push([Date.parse(sell['created_on']), buy['price_usd_formatted'], sell['price_usd_formatted']]);
            resEur.push([Date.parse(sell['created_on']), buy['price_eur_formatted'], sell['price_eur_formatted']]);
        }

        return {
            rub: resRub,
            usd: resUsd,
            eur: resEur
        }
    }

    function updateOrder (elem, isInitial) {
        var val,
            rate,
            floor = 100000000;

        isInitial = isInitial || !elem.val().trim();
        val = isInitial ? elem.attr('placeholder') : elem.val();

        if (!val) {
            return;
        }

        $.get(tickerLatestUrl, function(data) {
            // TODO: protect against NaN
            updatePrice(getPrice(data[ACTION_BUY]), $('.rate-buy'));
            updatePrice(getPrice(data[ACTION_SELL]), $('.rate-sell'));
            rate = data[action]['price_' + currency + '_formatted'];
            if (elem.hasClass('amount-coin')) {
                var cashAmount = rate * val;
                if (isInitial) {
                    $('.amount-cash').attr('placeholder', cashAmount);
                } else {
                    $('.amount-cash').val(cashAmount);
                }
            } else {
                var btcAmount = Math.floor(val / rate * floor) / floor;
                if (isInitial) {
                    $('.amount-coin').attr('placeholder', btcAmount);
                } else {
                    $('.amount-coin').val(btcAmount);
                }
            }
            $('.btc-amount-confirm').text($('.amount-coin').val()); // add
            $('.cash-amount-confirm').text($('.amount-cash').val()); //add
        });
    }

    function updatePrice (price, elem) {
        var currentPriceText = elem.html().trim(),
            currentPrice,
            isReasonableChange;

        if (currentPriceText != '') {
            currentPrice = parseFloat(currentPriceText);
        } else {
            elem.html(price);
            return;
        }
        // TODO: refactor this logic
        isReasonableChange = price < currentPrice * 1.05;
        if (currentPrice < price && isReasonableChange) {
            animatePrice(price, elem, true);
        }
        else if (!isReasonableChange) {
            setPrice(elem, price);
        }

        isReasonableChange = price * 1.05 > currentPrice;
        if (currentPrice > price && isReasonableChange) {
            animatePrice(price, elem);
        }
        else if (!isReasonableChange) {
            setPrice(elem, price);
        }
    }

    function animatePrice (price, elem, isRaise) {
        var animationClass = isRaise ? 'up' : 'down';
        elem.addClass(animationClass).delay(animationDelay).queue(function (next) {
                        setPrice(elem, price).delay(animationDelay / 2).queue(function(next) {
                elem.removeClass(animationClass);
                next();
            });
            next();
        });
    }
    window.updatePrice = updatePrice;
    function getPrice (data) {
        return data['price_' + currency + '_formatted'];
    }

    function setCurrency (elem) {
        if (elem && elem.hasClass('currency_pair')) {
            $('.currency_to').val(elem.data('crypto'));
        }

        $('.currency').html(currency.toUpperCase());
        renderChart();
    }

    function setPrice(elem, price) {
        elem.each(function () {
            if ($(this).hasClass('amount-cash')) {
                price = price * $('.amount-coin');
                price = Math.round(price * 100) / 100;
            } else {
                $(this).html(price);
            }
        });

        return elem;
    }


    function loadPaymenMethods(paymentMethodsEndpoint) {
        $.get(paymentMethodsEndpoint, function (data) {
            $(".paymentMethods").html($(data));
        });
        $('.paymentMethods').removeClass('hidden');
    }

    function loadPaymenMethodsAccount(paymentMethodsAccountEndpoint,pm) {
        data = {'payment_method': pm};
        $.get(paymentMethodsAccountEndpoint, data,function (data) {
            $(".paymentMethodsAccount").html($(data));
        });
        $('.paymentMethodsAccount').removeClass('hidden');
    }

    function renderChart () {
         $.get(tickerHistoryUrl, function(resdata) {
            chartDataRaw = resdata;
            var data = responseToChart(resdata)[currency];
          $('#container').highcharts({

                chart: {
                    type: 'arearange',
                    zoomType: 'x',
                  backgroundColor: {
                     linearGradient: { x1: 0, y1: 0, x2: 1, y2: 1 },
                     stops: [
                        [0, '#e3ffda'],
                        [1, '#e3ffda']
                     ]
                  },
                    events : {
                        load : function () {
                            // set up the updating of the chart each second
                            var series = this.series[0];
                            setInterval(function () {
                                $.get(tickerLatestUrl, function (resdata) {
                                    var lastdata = responseToChart(resdata)[currency];
                                    if ( chartDataRaw.length && parseInt(resdata[0]["unix_time"]) >
                                         parseInt(chartDataRaw[chartDataRaw.length - 1]["unix_time"])
                                    ) {
                                        //Only update if a ticker 'tick' had occured
                                        series.addPoint(lastdata[0], true, true);
                                        Array.prototype.push.apply(chartDataRaw, resdata);
                                    }

                                });
                        }, 1000 * 30);
                      }
                    }
                },

                title: {
                    text: 'BTC/' + currency.toUpperCase()
                },

                xAxis: {
                    type: 'datetime',
                    dateTimeLabelFormats: {
                       day: '%e %b',
                        hour: '%H %M'

                    }
                },
                yAxis: {
                    title: {
                        text: null
                    }
                },

                tooltip: {
                    crosshairs: true,
                    shared: true,
                    valueSuffix: ' ' + currency.toLocaleUpperCase()
                },

                legend: {
                    enabled: false
                },

                series: [{
                    name: currency === 'rub' ? 'цена' : 'Price',
                    data: data,
                    color: 'lightgreen',
                    // TODO: fix this!
                    pointInterval: 3600 * 1000 
                }]
            });
        });
    }
} (window, window.jQuery));

},{}],6:[function(require,module,exports){
function Order() {
    this.paymentMethodId = null;
    this.orderType = null;
    this.createdPaymentMethod = null;
    this.amountCoin = null;
}
},{}],7:[function(require,module,exports){
function PaymentPreference () {
    this.paymentMethodId = null;
    this.indentifier = null;
}
},{}],8:[function(require,module,exports){

var requestNewSMSToken = function() {
    var url = $("#resend_sms_button").data('url');

    $("#resend_sms_button").html(
        '<i class="fa fa-spinner fa-spin"></i>&nbsp;Sending you the token again...'
    );

    $.post( url , function( data ) {
        $("#resend_sms_button").html(
            '<i class="fa fa-repeat" aria-hidden="true"></i>&nbsp;Send-me the token again'
        );
        window.alert("SMS token sent. Fill in the verification form field and click on 'Verify phone now'.")
    }).fail(function(){
        
        $("#resend_sms_button").html(
            '<i class="fa fa-repeat" aria-hidden="true"></i>&nbsp;Send-me the verification token again'
        );
        window.alert("Something went wrong. Please, try again.")
    });
};


$("#resend_sms_button").on("click", requestNewSMSToken);

var verifyPhone = function() {
    var url = $("#verify_phone_now").data('url');
    var token = $("#verification_code").val();

    $("#alert_phone_not_verified").hide();
    $("#alert_verifying_phone").show();

     $.post( url , {'token': token}, function( data ) {
        if (data.status === 'OK') {
            window.location.reload(); //TODO: Ajax update screen..
        } else if (data.status === 'NOT_MATCH') {
            $("#alert_verifying_phone").hide();
            $("#alert_phone_not_verified").show();
            window.alert("The code you sent was incorrect. Please, try again.")
        }

        
    }).fail(function(){
        $("#alert_verifying_phone").hide();
        $("#alert_phone_not_verified").show();
        window.alert("Something went wrong. Please, try again.")
    });
   
};

$("#verify_phone_now").on("click", verifyPhone);

},{}]},{},[1,2,3,4,5,8,6,7]);
