(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
!(function (window, $) {
    'use strict';

    $(document).ajaxStart(function () {
        NProgress.start();
    });
    $(document).ajaxComplete(function () {
        setTimeout(function () {
            NProgress.done();
        }, 500);
    });
       var url = window.location.href,
           urlFragments = url.split('/'),
           pairPos = urlFragments.length - 2,
           pair = urlFragments[pairPos],
           currency = pair.substring(3, 6),
           currency_to = pair.substring(0, 3),
           currencyElem,
           paymentMethodsAccountEndpoint = '/en/paymentmethods/account/ajax/',
           cardsEndpoint = '/en/payments/options/',
           // Required modules
           orderObject = require('./modules/orders.js'),
           paymentObject = require('./modules/payment.js'),
           captcha = require('./modules/captcha.js'),
           $currencyFrom,
           $currencyTo,
           $currencyPair,
           $currencySelect;

        $('.trade-type').val('1');

        window.ACTION_BUY = 1;
        window.ACTION_SELL = 0;
        window.action = window.ACTION_BUY; // 1 - BUY 0 - SELL

    $(function () {
        if (currencyElem && currencyElem.val()){
                currency = currencyElem.val().toLowerCase();
        }

        $currencySelect = $('.currency-select');
        $currencyFrom = $('.currency-from');
        $currencyTo = $('.currency-to');
        $currencyPair = $('.currency-pair');
        $currencyFrom.val(currency);
        $currencyPair.val(pair);
        $currencyTo.val(currency_to);
        orderObject.setCurrency(false, currency, currency_to, pair);
        paymentObject.loadPaymentMethods(cardsEndpoint, currency);
        var timer = null,
            delay = 500,
            phones = $('.phone'),
            verification_code = $('#verification_code');
        //if not used idx: remove jshint
        phones.each(function () {
            if(typeof $(this).intlTelInput === 'function') {
                // with AMD move to https://codepen.io/jackocnr/pen/RNVwPo
                $(this).intlTelInput();
                $(this).intlTelInput("setCountry", window.countryCode);
            }
        });
         var stripSpaces = function stripSpaces() {
            var val = $(this).val();
            val = val.split(' ').join('');
            $(this).val(val);
        };
        phones.on('keyup', stripSpaces);
        verification_code.on('keyup', stripSpaces);


        orderObject.updateOrder($('.amount-coin'), true, currency);
        // if not used event, isNext remove  jshint
        $('#graph-range').on('change', function() {
            orderObject.setCurrency(false, currency, currency_to, pair);
        });

        $('.exchange-sign').click(function () {
            var menuElem = $('.menu1');

            window.action = menuElem.hasClass('sell') ?
                window.ACTION_BUY : window.ACTION_SELL;

            orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    menuElem.toggleClass('sell');
            });
        });

        $('.trigger').click( function(){
            $('.trigger').removeClass('active-action');
            $(this).addClass('active-action');
            if ($(this).hasClass('trigger-buy')) {
                $('.menu1').removeClass('sell');
                window.action = window.ACTION_BUY;
                orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    orderObject.toggleBuyModal();
                });

            } else {
                $('.menu1').addClass('sell');
                window.action = window.ACTION_SELL;
                orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    orderObject.toggleSellModal();
                });
            }

            $('.trade-type').val(window.action);

            orderObject.updateOrder($('.amount-coin'), true, currency);

            var newCashClass = window.action === window.ACTION_BUY ? 'rate-buy' : 'rate-sell';
              $('.amount-cash, .amount-coin')
                .removeClass('rate-buy')
                .removeClass('rate-sell')
                .addClass(newCashClass);
        });

        $('.amount').on('keyup', function () {
            // Protection against non-integers
            // TODO: export outside
            var val = this.value,
                lastChar = val.slice(-1),
                prevVal = val.substr(0, val.length-1);
            if(!!prevVal && lastChar === '.' &&
                prevVal.indexOf('.') === -1) {
                return;
                // # TODO: User isNaN
            } else if(!parseInt(lastChar) &&
                      parseInt(lastChar) !== 0) {
                // TODO: animate error
                $(this).val(prevVal);
                return;
            }
            var self = this,
                loaderElem = $('.exchange-sign'),
                cb = function animationCallback() {
                    loaderElem.one('animationiteration webkitAnimationIteration', function() {
                        loaderElem.removeClass('loading');
                    });

                    setTimeout(function () {
                        loaderElem.removeClass('loading');
                    }, 2000);// max animation duration
                };

            loaderElem.addClass('loading');
            if (timer) {
                clearTimeout(timer);
                timer = null;
            }
            timer = setTimeout(function () {
                orderObject.updateOrder($(self), false, currency, cb);
            }, delay);
        });

         $('.payment-method').on('change', function () {
            paymentObject.loadPaymentMethodsAccount(paymentMethodsAccountEndpoint);

        });

        $currencySelect.on('change', function () {
            if ($(this).hasClass('currency-pair')) {
                var selected = $(this).find('option:selected');
                currency = selected.attr('data-fiat');
                pair = selected.val();
                currency_to = selected.attr('data-crypto');
            } else if ($(this).hasClass('currency-from')) {
                currency = $(this).val();
                currency_to = $('.currency-to').val();
                pair = currency_to + currency;
            } else if ($(this).hasClass('currency-to')) {
                currency_to = $(this).val();
                currency = $('.currency-from').val();
                pair = currency_to + currency;

            }
            orderObject.setCurrency($(this), currency, currency_to, pair);
            paymentObject.loadPaymentMethods(cardsEndpoint, currency);
            //bind all select boxes
            $currencyFrom.val(currency);
            $currencyPair.val(pair);
            $currencyTo.val(currency_to);
            orderObject.updateOrder($('.amount-coin'), false, currency);
            // orderObject.reloadCardsPerCurrency(currency, cardsEndpoint);
        });
        //using this form because the object is inside a modal screen
        $(document).on('change','.payment-method', function () {
            var pm = $('.payment-method option:selected').val();
            $('#payment_method_id').val(pm);
            paymentObject.loadPaymentMethodsAccount(paymentMethodsAccountEndpoint, pm);

        });

    });

    $(function() {
        function lockoutResponse (data) {
            toastr.error(window.getLockOutText(data));
        }

        function failureResponse (data, defaultMsg) {
            var _defaultMsg = gettext(defaultMsg),
                message = data.responseJSON.message || _defaultMsg;
            toastr.error(message);

        }

        // For order index
        $('[data-toggle="popover"]').popover({content: $("#popover-template").html()});
        $( "#id_date" ).datepicker({ dateFormat: 'yy-mm-dd' });

        // TODO: get api root via DI
        $('#payment_method_id').val('');
        $('#user_address_id').val('');
        $('#new_user_account').val('');
        // TODO: if no amount coin selected DEFAULT_AMOUNT to confirm
        var amountCoin = $('.amount-coin'),
            confirm = amountCoin.val() ? amountCoin.val() : DEFAULT_AMOUNT;
        $('.btc-amount-confirm').text(confirm);

        var apiRoot = '/en/api/v1',
            createAccEndpoint =  '/en/accounts/authenticate/',
            menuEndpoint = apiRoot + '/menu',
            breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
            validatePhoneEndpoint = '/en/accounts/verify_phone/',
            placerAjaxOrder = '/en/orders/add_order/',
            paymentAjax = '/en/payments/ajax/',
            DEFAULT_AMOUNT = 1;

        $('.next-step, .prev-step').on('click', orderObject.changeState);
        $('.phone.val').on('keyup', function () {
            if($(this).val().length) {
                $('.create-acc')
                    .not('.resend')
                    .removeClass('disabled');
            }
        });
        $('.create-acc').on('click', function () {
            if($(this).hasClass('disabled')) {
                return;
            }
            $('.phone.val').addClass('disabled');


            var regPayload = {
                // TODO: check collision with qiwi wallet
                phone: $('.register .phone').val(),
                g_recaptcha_response: grecaptcha.getResponse(),
            };
            $.ajax({
                type: 'POST',
                dataType: 'json',
                url: createAccEndpoint,
                data: regPayload,
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
                    410: function (data) {
                        return failureResponse(
                            data,
                            'Your token has expired, please request a new one'
                        );
                    },
                    428: function (data) {
                        return failureResponse(
                            data,
                            'Invalid phone number'
                        );
                    },

                }
            });
        });

        $('.verify-acc').on('click', function () {
            var verifyPayload = {
                token: $('#verification_code').val(),
                phone: $('.register .phone').val()
            };
            $.ajax({
                type: 'POST',
                dataType: 'json',
                url: validatePhoneEndpoint,
                data: verifyPayload,
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
                    403: lockoutResponse
                }
            });

        });


        $('.place-order').on('click', function () {
            //TODO verify if $(this).hasClass('sell-go') add
            // the other type of transaction
            // add security checks
            var actualPaymentType = $('.payment-preference-actual').text(),
                preferenceIdentifier = $('.payment-preference-identifier-confirm').text(),
                preferenceOwner = $('.payment-preference-owner-confirm').text(),
                verifyPayload = {
                    'trade-type': $('.trade-type').val(),
                    'csrfmiddlewaretoken': $('#csrfmiddlewaretoken').val(),
                    'amount-base': $('.amount-coin').val() || DEFAULT_AMOUNT,
                    'currency_from': $('.currency-from').val(), //fiat
                    'currency_to': $('.currency-to').val(), //crypto
                    'pp_type': actualPaymentType,
                    'pp_identifier': preferenceIdentifier,
                    'pp_owner': preferenceOwner,
                    '_locale': $('.topright_selectbox').val()
                };

            $.ajax({
                type: 'post',
                url: placerAjaxOrder,
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function (data) {
                    //if the transaction is Buy
                      var message;
                    if (window.action == window.ACTION_BUY){
                        message = gettext('Buy order placed successfully');
                    }
                    //if the transaction is Sell
                    else{
                        message = gettext('Sell order placed successfully');

                    }
                    toastr.success(message);
                    $('.successOrder').html($(data));
                    $('#orderSuccessModal').modal({backdrop: 'static'});

                },
                error: function () {
                	var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });

        });

      $('.make-payment').on('click', function () {
            var verifyPayload = {
                'order_id': $('.trade-type').val(),
                'csrfmiddlewaretoken': $('#csrfmiddlewaretoken').val(),
                'amount-cash': $('.amount-cash').val(),
                'currency_from': $('.currency-from').val(),
            };

            $.ajax({
                type: 'post',
                url: paymentAjax,
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function (data) {
                    $('.paymentMethodsHead').addClass('hidden');
                    $('.paymentMethods').addClass('hidden');
                    $('.paymentSuccess').removeClass('hidden').html($(data));
                    $('.next-step').click();
                },
                error: function () {
                	var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });

        });

        $(document).on('click', '.buy .payment-type-trigger', function () {
            var paymentType = $(this).data('label'),
            actualPaymentType = $(this).data('type'),
            preferenceIdentifier = $(this).data('identifier');
            $('.payment-preference-confirm').text(paymentType);
            $('.payment-preference-actual').text(actualPaymentType);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);
            $('#PayMethModal').modal('toggle');
            $('.payment-method').val(paymentType);
            orderObject.changeState(null, 'next');
        });
        // $(document).on('click', '.payment-type-trigger-footer', paymentNegotiation);

        $('.sell .payment-type-trigger').on('click', function () {
            var paymentType = $(this).data('type').toLocaleLowerCase(),
                modalId = paymentType + 'SellModal',
                modal = $('#' + modalId);
            $(this).closest('.modal').modal('hide');
            modal.modal('show');
        });

        $('.sellMethModal .back').click(function () {
            $(this).closest('.modal').modal('toggle');
            $('#UserAccountModal').modal('toggle');
        });

        $('.payment-widget .val').on('keyup, keydown', function() {
            var val = $(this).closest('.val');
            if (!val.val().length) {
               $(this).removeClass('error').removeClass('valid');
                return;
            }
           if (val.hasClass('jp-card-invalid')) {
                $(this).removeClass('valid').addClass('error');
                // $('.save-card').addClass('disabled');
            } else {
               $(this).removeClass('error').addClass('valid');
               // $('.save-card').removeClass('disabled');
           }

        });

        $('.payment-widget .save-card').on('click', function () {
            $('.supporetd_payment').addClass('hidden');
            // TODO: Add handling for qiwi wallet with .intlTelInput('getNumber')
            if ($(this).hasClass('disabled')) {
                return false;
            }

            var form = $(this).closest('.modal-body'),
                preferenceIdentifier = form.find('.val').val(),
                preferenceOwner = form.find('.name').val();

            $('.payment-preference-owner').val(preferenceOwner);
            $('.payment-preference-identifier').val(preferenceIdentifier);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);

            $(this).closest('.modal').modal('hide');
            
            setTimeout(function () {
                orderObject.changeState(null, 'next');
            }, 600);
        });
    });

    //for tests selenium
    function submit_phone(){
        var apiRoot = '/en/api/v1',
            menuEndpoint = apiRoot + '/menu',
            breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
            validatePhoneEndpoint = '/en/profile/verifyPhone/';
            var verifyPayload = {
                token: $('#verification_code').val(),
                phone: $('.register .phone').val()
            };
            $.ajax({
                type: 'POST',
                url: validatePhoneEndpoint,
                data: verifyPayload,
                success: function (data) {
                    if (data.status === 'OK') {
                        orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                        orderObject.changeState('next');
                    } else {
                	    var message = gettext('The code you sent was incorrect. Please, try again.');
                        toastr.error(message);
                    }
                },
                error: function () {
                	var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });

    }

    window.submit_phone=submit_phone;
} (window, window.jQuery)); //jshint ignore:line



},{"./modules/captcha.js":2,"./modules/orders.js":4,"./modules/payment.js":5}],2:[function(require,module,exports){
!(function(window ,$) {
  "use strict";
    var isVerified = false;

  var verifyRecatpchaCallback = function(response) {

          //console.log( 'g-recaptcha-response: ' + response );
      if($('.phone.val').val().length > 10) {
            $('.create-acc')
                .not('.resend')
                .removeClass('disabled');
      }

      isVerified = true;
  };
  
  var getIsVerefied = function () {
      return isVerified;
  };

var doRender = function() {
      grecaptcha.render( 'grecaptcha', {
        'sitekey' : window.recaptchaSitekey,  // required
        'theme' : 'light',  // optional
        'callback': verifyRecatpchaCallback  // optional
      });
};

module.exports = {
    verifyRecatpchaCallback:verifyRecatpchaCallback,
    doRender: doRender,
    isVerified: getIsVerefied
};

}(window, window.jQuery)); //jshint ignore:line

},{}],3:[function(require,module,exports){
!(function(window ,$) {
    "use strict";

    var apiRoot = '/en/api/v1/price/',
        chartDataRaw;

    function responseToChart(data) {
        var i,
            resPair = [];
        for (i = 0; i < data.length; i+=2) {
            var price = data[i],
                ask = parseFloat(price.ticker.ask),
                bid = parseFloat(price.ticker.bid);
            resPair.push([Date.parse(price.created_on), ask, bid]);
        }
        return {
            pair: resPair,
        };
    }

    function renderChart (pair, title, hours) {
        var tickerHistoryUrl= apiRoot + pair + '/history',
            tickerLatestUrl = apiRoot + pair + '/latest';
        if (hours) {
            tickerHistoryUrl = tickerHistoryUrl + '?hours=' + hours;
        }
         $.get(tickerHistoryUrl, function(resdata) {
            chartDataRaw = resdata;

            var data = responseToChart(resdata).pair,
                container = $('#container-graph');
             if (!container || !container.length) {
                 return;
             }
             container.highcharts({

                 chart: {
                     type: 'arearange',
                     zoomType: 'x',
                     style: {
                         fontFamily: 'Gotham'
                     },
                     backgroundColor: {
                         linearGradient: {x1: 0, y1: 0, x2: 1, y2: 1},
                         stops: [
                             [0, '#F3F3F3'],
                             [1, '#F3F3F3']
                         ]
                     },
                     events: {
                         load: function () {
                             // set up the updating of the chart each second
                             $('.highcharts-credits').remove();
                             var series = this.series[0];
                             var intervalId = setInterval(function () {
                                 if (pair != $('.currency-pair option:selected').val()) {
                                    clearInterval(intervalId);
                                 } else {
                                     $.get(tickerLatestUrl, function (resdata) {
                                         var lastdata = responseToChart(resdata).pair;
                                         if (chartDataRaw.length && parseInt(resdata[0].unix_time) >
                                             parseInt(chartDataRaw[chartDataRaw.length - 1].unix_time)
                                         ) {
                                             //Only update if a ticker 'tick' had occured
                                             var _lastadata = lastdata[0];
                                             if (_lastadata[1] > _lastadata[2]) {
                                                 var a = _lastadata[1];
                                                 _lastadata[1] = _lastadata[2];
                                                 _lastadata[2] = a;
                                             }
                                             series.addPoint(_lastadata, true, true);
                                             Array.prototype.push.apply(chartDataRaw, resdata);
                                         }
                                     });
                                 }
                             }, 1000 * 10);
                         }
                     }
                 },

                 title: {
                     text: title
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
                     valueSuffix: ' ' + pair
                 },

                 legend: {
                     enabled: false
                 },

                 series: [{
                     name: pair,
                     data: data,
                     color: '#8cc63f',
                     // TODO: fix this! make dynamic
                     pointInterval: 3600 * 1000
                 }]
             });
        });
    }

    module.exports = {
        responseToChart:responseToChart,
        renderChart: renderChart,
        apiRoot: apiRoot,
        chartDataRaw: chartDataRaw
    };
}(window, window.jQuery)); //jshint ignore:line

},{}],4:[function(require,module,exports){
!(function(window, $) {
    "use strict";

      // Required modules
     var chartObject = require("./chart.js"),
         registerObject = require("./register.js"),
         googleObject = require('./captcha.js'),
         currency = null,
         animationDelay = 3000,
         minOrderCoin = 0.0001;

    function orderSmallerThanMin (amountCoin) {
        var val = parseFloat(amountCoin.val());
        return val < minOrderCoin;
    }

    function updateOrder (elem, isInitial, currency, cb) {
        var val,
            rate,
            msg,
            pair,
            amountCoin = $('.amount-coin'),
            amountCashConfirm = 0,
                floor = 100000000;

        isInitial = isInitial || !elem.val().trim();
        val = isInitial ? elem.attr('placeholder') : elem.val();
        val = parseFloat(val);
        if (!val) {
            return;
        }

        if(orderSmallerThanMin(amountCoin)) {
             val = minOrderCoin;
             elem = amountCoin;

            msg = gettext('Minimal order amount is ') + minOrderCoin + ' BTC';
            toastr.error(msg);
        }

        if ($('.currency-pair option:selected').val()) {
            pair = $('.currency-pair option:selected').val();
        } else {
             var base = $('.currency-to').val(),
                 quote = $('.currency-from').val();
             pair = base + quote;
        }
        var tickerLatestUrl = chartObject.apiRoot + pair + '/latest';

        $.get(tickerLatestUrl, function(data) {
            // TODO: protect against NaN
            updatePrice(parseFloat(data[0].ticker.ask), $('.rate-buy'));
            updatePrice(parseFloat(data[0].ticker.bid), $('.rate-sell'));
            rate = parseFloat(data[0].ticker.ask);
            if (window.action == window.ACTION_SELL) {
                rate = parseFloat(data[0].ticker.bid);
            }
            var btcAmount,
                cashAmount;
            if (elem.hasClass('amount-coin')) {
                btcAmount = val.toFixed(8);
                cashAmount = (rate * btcAmount).toFixed(2);
                amountCashConfirm = cashAmount;
                $(this).val(btcAmount);
                if (isInitial) {
                    $('.amount-cash').attr('placeholder', cashAmount);
                } else {
                    $('.amount-cash').val(cashAmount);
                    $('.amount-coin').val(btcAmount);
                }
            } else {
                amountCashConfirm = val;
                btcAmount = Math.floor(val / rate * floor) / floor;
                btcAmount = btcAmount.toFixed(8);
                if (isInitial) {
                    $('.amount-coin').attr('placeholder', btcAmount);
                } else {
                    $('.amount-coin').val(btcAmount);
                }
            }
            $('.btc-amount-confirm').text(amountCoin.val()); // add
            $('.cash-amount-confirm').text(amountCashConfirm); //add

            if(cb) cb();
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

    function setCurrency (elem, currency, currency_to, pair) {
        if (elem && elem.hasClass('currency_pair')) {
            $('.currency_to').val(elem.data('crypto'));

        }
        if (!!currency) {
            $('.currency').html(currency.toUpperCase());
            var title = currency_to + '/' + currency;
            chartObject.renderChart(pair, title, $("#graph-range").val());
        }
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
            googleObject.doRender();                 
            var modifier = window.ACTION_SELL ? 'btn-danger' : 'btn-success';
            $('.next-step').removeClass('btn-info').addClass(modifier);                        
        } else {
            $('.next-step').removeClass('btn-success').removeClass('btn-danger').addClass('btn-info');
        }
        $('.btn-circle.btn-info')
            .removeClass('btn-info')
            .addClass('btn-default');
    }

    function toggleBuyModal () {
        $("#PayMethModal").modal('toggle');
    }

    function toggleSellModal () {
        try{
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
        }
        catch(e) {}
        $("#UserAccountModal").modal({backdrop: "static"});
    }

    function changeState (e, action) {       
        if (e) {
            e.preventDefault();
        }
        if ( $(this).hasClass('disabled') ) {// jshint ignore:line
            //todo: allow user to buy placeholder value or block 'next'?
            return;
        }

        if (!$('.payment-preference-confirm').html().trim()) {
            if (window.action == window.ACTION_BUY){
                toggleBuyModal();
            } else {
                toggleSellModal();
            }            
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
            action = action || $(this).hasClass('next-step') ? 'next' : 'prev',// jshint ignore:line
            nextStateId = tab[action](paneClass).attr('id'),
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
            changeState(null, action);            
        }


        if (nextStateTrigger.hasClass('hidden')) {
            nextStateTrigger.removeClass('hidden');
        }


        if ( !registerObject.canProceedtoRegister(currStateId) ){
            $('.trigger-buy').trigger('click', true);
        } else {
            setButtonDefaultState(nextStateId);

            currState
                .addClass('completed');

            nextState
                .tab('show');
            window.scrollTo(0, 0);
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

        $(".step2 .btn")
            .addClass('btn-info')
            .addClass('disableClick');
    }

    function placeOrder () {
            //TODO verify if $(this).hasClass('sell-go') add
            // the other type of transaction
            // add security checks
            var actualPaymentType = $('.payment-preference-actual').val(),
            preferenceIdentifier = $('.payment-preference-identifier-confirm').text(),
            preferenceOwner = $('.payment-preference-owner-confirm').text();

            var verifyPayload = {
                    'trade-type': $('.trade-type').val(),
                    'csrfmiddlewaretoken': $('#csrfmiddlewaretoken').val(),
                    'amount-coin': $('.amount-coin').val() || DEFAULT_AMOUNT,
                    'currency_from': $('.currency-from').val(), //fiat
                    'currency_to': $('.currency-to').val(), //crypto
                    'pp_type': actualPaymentType,
                    'pp_identifier': preferenceIdentifier,
                    'pp_owner': preferenceOwner,
                    '_locale': $('.topright_selectbox').val()
                };

            $.ajax({
                type: 'post',
                url: placerAjaxOrder,
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function (data) {
                    //if the transaction is Buy
                      var message;
                    if (window.action == window.ACTION_BUY){
                        message = gettext('Buy order placed successfully');
                    }
                    //if the transaction is Sell
                    else{
                        message = gettext('Sell order placed successfully');

                    }
                    toastr.success(message);
                    $('.successOrder').html($(data));
                    $('#orderSuccessModal').modal({backdrop: 'static'});

                },
                error: function () {
                	var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
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
        toggleBuyModal: toggleBuyModal,
        toggleSellModal: toggleSellModal
    };
}(window, window.jQuery)); //jshint ignore:line

},{"./captcha.js":2,"./chart.js":3,"./register.js":6}],5:[function(require,module,exports){
!(function(window ,$) {
    "use strict";

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

},{}],6:[function(require,module,exports){
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
