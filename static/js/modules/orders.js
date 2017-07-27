!(function(window, $) {
    "use strict";

      // Required modules
     var chartObject = require("./chart.js"),
         registerObject = require("./register.js"),
         googleObject = require('./captcha.js'),
         paymentObj = require('./payment.js'),
         apiRoot = '/en/api/v1',
         menuEndpoint = apiRoot + '/menu',
         currency = null,
         animationDelay = 3000,
         beamerShowDelay = 1000,
         minOrderCash = 10;

    $(function() {
        function setAsPaidFlow () {
            if (!rootElem || !rootElem.length) {
                return;
            }
            $('html, body').animate({
                scrollTop: rootElem.offset().top
            })
            .delay(indicateWithdrawDelay)
            .queue(function (next) {
                rootElem.click();
                next();
            })
            .delay(payDelay)
            .queue(function (next) {
                toggleElem =  $('.toggle-group').filter(':visible').siblings('.pay-setter');
                if (isPaid && !toggleElem.is(':checked')) {
                    toggleElem.parent().click();
                    next();
                }
            })
            .delay(beamerShowDelay)
                .queue(function (next) {
                    $('.scenes-wrapper').fadeIn();
                    next();
                });
        }

        var params = parseQuery(window.location.search),
            oid = params.oid,
            initialDelay = 1500,
            payDelay = 1500,
            isPaid =  params.is_paid,
            indicateWithdrawDelay = isPaid ? 1500 : 0,
            oidSelector = '#' + oid,
            rootElem = $(oidSelector),
            toggleElem;


        if (oid) {
            setTimeout(function() {setAsPaidFlow();}, initialDelay);
        }
    });

    function orderSmallerThanMin (amount, minOrder) {
        var val = parseFloat(amount.val());
        return val < minOrder;
    }

    function getDecimalPlaces (amount) {
        var decimalPlaces = 2,
            invertedDecimalSize = -Math.floor(Math.log10(amount));
        if (invertedDecimalSize > 0) {
            decimalPlaces = decimalPlaces + invertedDecimalSize;
        }
        return decimalPlaces;
    }

    function updateOrder (elem, isInitial, currency, cb) {
        var val,
            rate,
            pair,
            amountCoin = $('.amount-coin'),
            amountCash = $('.amount-cash'),
            amountCashConfirm = 0,
            minOrderCoin = parseFloat($('.currency-to').find('option:selected').attr('data-minimal-amount')),
                floor = 100000000;

        isInitial = isInitial || !elem.val().trim();
        val = isInitial ? elem.attr('placeholder') : elem.val();
        val = parseFloat(val);
        if (!val) {
            return;
        }

        var msgBase = gettext('Minimal order amount is '),
            minOrderCoins = msgBase + minOrderCoin + ' ' + gettext('Coins'),
            minOrderCash = msgBase + minOrderCash;

        if(orderSmallerThanMin(amountCoin, minOrderCoin)) {
             val = minOrderCoin;
             elem = amountCoin;
            toastr.error(minOrderCoins);
        } else if (orderSmallerThanMin(amountCash, minOrderCash)) {
             val = minOrderCash;
             elem = amountCash;
            toastr.error(minOrderCash);
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
            var ticker = data[0].ticker,
                rawBid = Number(ticker.bid),
                rawAsk = Number(ticker.ask),
                ask,
                bid,
                cashFixed = getDecimalPlaces(rawBid);
            bid = parseFloat(rawBid.toFixed(cashFixed));
            ask = parseFloat(rawAsk.toFixed(cashFixed));
            updatePrice(ask, $('.rate-buy'));
            updatePrice(bid, $('.rate-sell'));
            rate = parseFloat(data[0].ticker.ask);
            if (window.action == window.ACTION_SELL) {
                rate = parseFloat(data[0].ticker.bid);
            }
            var btcAmount,
                cashAmount,
                cashFixedCalc;
            if (elem.hasClass('amount-coin')) {
                btcAmount = parseFloat(val.toFixed(8));
                cashAmount = rate * btcAmount;
                cashFixedCalc = getDecimalPlaces(cashAmount);
                cashAmount = parseFloat(cashAmount.toFixed(cashFixedCalc));
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
                btcAmount = parseFloat(btcAmount.toFixed(8));
                if (isInitial) {
                    $('.amount-coin').attr('placeholder', btcAmount);
                } else {
                    $('.amount-coin').val(btcAmount);
                }
            }
            $('.btc-amount-confirm').text($('.amount-coin').val()); // add
            if ($('.amount-cash').val().length === 0) {
                $('.cash-amount-confirm').text(amountCashConfirm); //add
            } else {
                $('.cash-amount-confirm').text($('.amount-cash').val()); //add
            }

            if(cb) cb();
        });
    }

    //utils
    function parseQuery(qstr) {
            var query = {};
            var a = (qstr[0] === '?' ? qstr.substr(1) : qstr).split('&');
            for (var i = 0; i < a.length; i++) {
                var b = a[i].split('=');
                query[decodeURIComponent(b[0])] = decodeURIComponent(b[1] || '');
            }
            return query;
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
            $('.currency_base').html(currency_to.toUpperCase());
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
        $("#buy_options_modal").modal('toggle');
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
        catch(supress) {}
        $("#sell_options_modal").modal({backdrop: "static"});
    }

    function changeState (e, action) {    
        if (e) {
            e.preventDefault();
        }
        if ( $(this).hasClass('disabled') ) {// jshint ignore:line
            //todo: allow user to buy placeholder value or block 'next'?
            return;
        }

        if (!$('.payment-preference-confirm').html().trim() && window.action == window.ACTION_BUY) {
            toggleBuyModal();
            return;
        }
        else if (window.action == window.ACTION_SELL &&
            $('.payment-preference-confirm').html() == 'EXCHANGE') {
            $('.buy-go').addClass('hidden');
            $('.sell-go').removeClass('hidden');
        }
        else if (window.action == window.ACTION_SELL && !paymentObj.getPaymentPreference()) {
            toggleSellModal();
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

    function reloadRoleRelatedElements () {
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
