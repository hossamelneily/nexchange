(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
"use strict";

!(function (window, $) {
       var  currency = 'rub',
        paymentMethodsEndpoint = '/en/paymentmethods/ajax/',
        paymentMethodsAccountEndpoint = '/en/paymentmethods/account/ajax/',
        cardsEndpoint = '/en/api/v1/cards',
        // Required modules
        orderObject = require("./modules/orders.js"),
        paymentObject = require("./modules/payment.js"),
        paymentType = '',
        preferenceIdentifier = '',
        preferenceOwner = '';

        $(".trade-type").val("1");

        window.ACTION_BUY = 1;
        window.ACTION_SELL = 0;
        window.action = window.ACTION_BUY; // 1 - BUY 0 - SELL

    $(function () {
            orderObject.setCurrency(false, currency);
            orderObject.reloadCardsPerCurrency(currency, cardsEndpoint);

            var timer = null,
                delay = 500,
                phones = $(".phone");
                            //if not used idx: remove jshint
            phones.each(function () {
                if(typeof $(this).intlTelInput === 'function') {
                    // with AMD move to https://codepen.io/jackocnr/pen/RNVwPo
                    $(this).intlTelInput();
                }
            });
            orderObject.updateOrder($('.amount-coin'), true, currency);
                        // if not used event, isNext remove  jshint
            $('.trigger').click( function(){
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
                    paymentObject.loadPaymenMethods(paymentMethodsEndpoint);
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

                    //TODO: export to card module
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

                orderObject.updateOrder($('.amount-coin'), true, currency);

                var newCashClass = window.action === window.ACTION_BUY ? 'rate-buy' : 'rate-sell';
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
                    orderObject.updateOrder($(self), false, currency);
                }, delay);
            });

             $('.payment-method').on('change', function () {
                paymentObject.loadPaymenMethodsAccount(paymentMethodsAccountEndpoint);

            });

            $('.currency-select').on('change', function () {
                currency = $(this).val().toLowerCase();
                orderObject.setCurrency($(this), currency);
                //bind all select boxes
                $('.currency-select').not('.currency-to').val($(this).val());
                orderObject.updateOrder($('.amount-coin'), false, currency);
                orderObject.reloadCardsPerCurrency(currency, cardsEndpoint);
            });
            //using this form because the object is inside a modal screen
            $(document).on('change','.payment-method', function () {
                var pm = $('.payment-method option:selected').val();
                $('#payment_method_id').val(pm);
                paymentObject.loadPaymenMethodsAccount(paymentMethodsAccountEndpoint, pm);

            });

        });

    $(function() {
        // TODO: get api root via DI
        $('#payment_method_id').val("");
        $('#user_address_id').val("");
        $('#new_user_account').val("");
        //TO-DO: if no amount coin selected DEFAULT_AMOUNT to confirm
        var confirm = $('.amount-coin').val() ? $('.amount-coin').val() : DEFAULT_AMOUNT;
        $(".btc-amount-confirm").text(confirm);

        var apiRoot = '/en/api/v1',
            createAccEndpoint = apiRoot + '/phone',
            menuEndpoint = apiRoot + '/menu',
            breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
            validatePhoneEndpoint = '/en/profile/verifyPhone/',
            placerAjaxOrder = '/en/order/ajax/',
            paymentAjax = '/en/payment/ajax/',
            DEFAULT_AMOUNT = 1;

        $('.next-step, .prev-step').on('click', orderObject.changeState);

        $('.create-acc').on('click', function () {
            var regPayload = {
                // TODO: check collision with qiwi wallet
                phone: $('.register .phone').val()
            };
            $.ajax({
                type: "POST",
                url: createAccEndpoint,
                data: regPayload,
                //success: function (data) {
                success: function () {
                    $('.register .step2').removeClass('hidden');
                    $('.verify-acc').removeClass('hidden');
                    $(".create-acc").addClass('hidden');
                    $(".create-acc.resend").removeClass('hidden');
                },
                //error: function (jqXHR, textStatus, errorThrown) {
                error: function () {
                    window.alert('Invalid phone number');
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
                        orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                        orderObject.changeState('next');
                    } else {
                        window.alert("The code you sent was incorrect. Please, try again.");
                    }
                },
                error: function () {
                    window.alert("Something went wrong. Please, try again.");
                }
            });

        });


        $('.place-order').on('click', function () {
            //TODO verify if $(this).hasClass('sell-go') add
            // the othre type of transaction
            // add security checks
            paymentType = $('.payment-preference-confirm').text() ;
            preferenceIdentifier = $('.payment-preference-identifier-confirm').text();
            preferenceOwner = $('.payment-preference-owner-confirm').text();
            var verifyPayload = {
                    "trade-type": $(".trade-type").val(),
                    "csrfmiddlewaretoken": $("#csrfmiddlewaretoken").val(),
                    "amount-coin": $('.amount-coin').val() || DEFAULT_AMOUNT,
                    "currency_from": $('.currency-from').val(), //fiat
                    "currency_to": $('.currency-to').val(), //crypto
                    "pp_type": paymentType,
                    "pp_identifier": preferenceIdentifier,
                    "pp_owner": preferenceOwner
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
                        //$('#btcAddress').text(data.address);
                        $(".successOrderSell").html($(data));
                        $("#orderSuccessModalSell").modal({backdrop: "static"});
                    }

                },
                error: function () {
                    window.alert("Something went wrong. Please, try again.");
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
                    $('.next-step').click();

                   // loadPaymenMethods(paymentMethodsEndpoint);

                },
                error: function () {
                    window.alert("Something went wrong. Please, try again.");
                }
            });

        });

        $(document).on('click', '.buy .payment-type-trigger', function () {
            paymentType = $(this).data('type');
            preferenceIdentifier = $(this).data('identifier');
            $(".payment-preference-confirm").text(paymentType);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);
            $("#PayMethModal").modal('toggle');
            $(".payment-method").val(paymentType);
            orderObject.changeState("next");
        });

        $('.sell .payment-type-trigger').on('click', function () {
            paymentType = $(this).data('type').toLocaleLowerCase();
            $(".payment-preference-confirm").text(paymentType);
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
            preferenceIdentifier = $(this).find('.val').val();
            preferenceOwner = $(this).find('.name').val();

            $(".payment-preference-owner").val(preferenceOwner);
            $(".payment-preference-identifier").val(preferenceIdentifier);
            $(".payment-preference-identifier-confirm").text(preferenceIdentifier);

            $(this).closest('.modal').modal('dismiss').delay(500).queue( function (next){
                orderObject.changeState("next");
                next();
            });
        });
    });

} (window, window.jQuery)); //jshint ignore:line
},{"./modules/orders.js":3,"./modules/payment.js":4}],2:[function(require,module,exports){
!(function(window ,$) {
    "use strict";

    var apiRoot = '/en/api/v1',
        chartDataRaw,
        tickerHistoryUrl = apiRoot +'/price/history',
        tickerLatestUrl = apiRoot + '/price/latest';

    function responseToChart(data) {
        var i,
            resRub = [],
            resUsd = [],
            resEur = [];

        for (i = 0; i < data.length; i+=2) {
            var sell = data[i],
            buy = data[i + 1];
            resRub.push([Date.parse(sell.created_on), buy.price_rub_formatted, sell.price_rub_formatted]);
            resUsd.push([Date.parse(sell.created_on), buy.price_usd_formatted, sell.price_usd_formatted]);
            resEur.push([Date.parse(sell.created_on), buy.price_eur_formatted, sell.price_eur_formatted]);
        }
        return {
            rub: resRub,
            usd: resUsd,
            eur: resEur
        };
    }

    function renderChart (currency) {
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
                                    if ( chartDataRaw.length && parseInt(resdata[0].unix_time) >
                                         parseInt(chartDataRaw[chartDataRaw.length - 1].unix_time)
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

    module.exports = {
        responseToChart:responseToChart,
        renderChart: renderChart,
        apiRoot: apiRoot,
        chartDataRaw: chartDataRaw,
        tickerHistoryUrl: tickerHistoryUrl,
        tickerLatestUrl: tickerLatestUrl
    };
}(window, window.jQuery)); //jshint ignore:line

},{}],3:[function(require,module,exports){
!(function(window, $) {
    "use strict";

      // Required modules
     var chartObject = require("./chart.js"),
         registerObject = require("./register.js"),
         animationDelay = 3000;

    function updateOrder (elem, isInitial, currency) {
        var val,
            rate,
            amountCoin = $('.amount-coin'),
            amountCashConfirm = 0,
            floor = 100000000;

        isInitial = isInitial || !elem.val().trim();
        val = isInitial ? elem.attr('placeholder') : elem.val();

        if (!val) {
            return;
        }

        $.get(chartObject.tickerLatestUrl, function(data) {
            // TODO: protect against NaN
            updatePrice(getPrice(data[window.ACTION_BUY], currency), $('.rate-buy'));
            updatePrice(getPrice(data[window.ACTION_SELL], currency), $('.rate-sell'));
            rate = data[window.action]['price_' + currency + '_formatted'];
            if (elem.hasClass('amount-coin')) {
                var cashAmount = rate * val;
                amountCashConfirm = cashAmount;
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
            $('.btc-amount-confirm').text(amountCoin.val()); // add
            $('.cash-amount-confirm').text(amountCashConfirm); //add
        });
    }

    //order.js

    function updatePrice (price, elem) {
        var currentPriceText = elem.html().trim(),
            currentPrice,
            isReasonableChange;

        if (currentPriceText !== '') {
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

    // order.js
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

    //order.js
    function getPrice (data, currency) {
        return data['price_' + currency + '_formatted'];
    }

    function setCurrency (elem, currency) {
        if (elem && elem.hasClass('currency_pair')) {
            $('.currency_to').val(elem.data('crypto'));

        }

        $('.currency').html(currency.toUpperCase());
        chartObject.renderChart(currency);
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

    function setButtonDefaultState (tabId) {
        if (tabId === 'menu2') {
            var modifier = window.ACTION_SELL ? 'btn-danger' : 'btn-success';
            $('.next-step').removeClass('btn-info').addClass(modifier);
        } else {
            $('.next-step').removeClass('btn-success').removeClass('btn-danger').addClass('btn-info');
        }
        $('.btn-circle.btn-info')
            .removeClass('btn-info')
            .addClass('btn-default');
    }

    function changeState (action) {
        if ( $(this).hasClass('disabled') ) {// jshint ignore:line
            //todo: allow user to buy placeholder value or block 'next'?
            return;
        }

        if (!$('.payment-preference-confirm').html().trim()) {
            $("#PayMethModal").modal('toggle');
            return;
        }

        var valElem = $('.amount-coin'),
            val;
        if (!valElem.val().trim()) {
            //set placeholder as value.
            val = valElem.attr('placeholder').trim();
            valElem.val(val).trigger('change');
            $('.btc-amount-confirm').html(val);
        }

        var paneClass = '.tab-pane',
            tab = $('.tab-pane.active'),
            action2 =  $(this).hasClass('next-step') ? 'next' :'prev',// jshint ignore:line
            nextStateId = tab[action2](paneClass).attr('id'),
            nextState = $('[href="#'+ nextStateId +'"]'),
            nextStateTrigger = $('#' + nextStateId),
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


        if (nextStateTrigger.hasClass('hidden')) {
            nextStateTrigger.removeClass('hidden');
        }


        if ( !registerObject.canProceedtoRegister(currStateId) ){
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

    function reloadRoleRelatedElements (menuEndpoint) {
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

    function reloadCardsPerCurrency(currency, cardsModalEndpoint) {
        $.post(cardsModalEndpoint, {currency: currency}, function (data) {
            $('.paymentSelectionContainer').html($(data));
        });
    }

    module.exports = {
        updateOrder: updateOrder,
        updatePrice: updatePrice,
        animatePrice: animatePrice,
        getPrice: getPrice,
        setCurrency: setCurrency,
        setPrice: setPrice,
        setButtonDefaultState: setButtonDefaultState,
        changeState: changeState,
        reloadRoleRelatedElements: reloadRoleRelatedElements,
        reloadCardsPerCurrency: reloadCardsPerCurrency
    };
}(window, window.jQuery)); //jshint ignore:line

},{"./chart.js":2,"./register.js":5}],4:[function(require,module,exports){
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

    module.exports =
    {
        loadPaymenMethods: loadPaymenMethods,
        loadPaymenMethodsAccount: loadPaymenMethodsAccount
    };

}(window, window.jQuery)); //jshint ignore:line

},{}],5:[function(require,module,exports){
!(function(window, $) {
    "use strict";

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

    module.exports = {
        canProceedtoRegister: canProceedtoRegister
    };
}(window, window.jQuery)); //jshint ignore:line
},{}]},{},[1]);
