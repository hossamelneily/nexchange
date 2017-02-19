!(function(window, $) {
    "use strict";

      // Required modules
     var chartObject = require("./chart.js"),
         registerObject = require("./register.js"),
         googleObject = require('./captcha.js'),
         paymentObj = require('./payment.js'),
         currency = null,
         animationDelay = 3000,
         minOrderCoin = 0.0001;

    $(function() {
        function setAsPaidFlow () {
            if (!rootElem || !rootElem.length) {
                return
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
            });
        }

        var params = new URLSearchParams(window.location.search),
            oid = params.get('oid'),
            initialDelay = 1500,
            payDelay = 1500,
            isPaid =  params.get('is_paid'),
            indicateWithdrawDelay = isPaid ? 1500 : 0,
            oidSelector = '#' + oid,
            rootElem = $(oidSelector),
            toggleElem;


        if (oid) {
            setTimeout(function() {setAsPaidFlow()}, initialDelay);
        }
    });
     
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
            var ticker = data[0].ticker,
                bid = Number(ticker.bid).toFixed(2),
                ask = Number(ticker.ask).toFixed(2);
            updatePrice(ask, $('.rate-buy'));
            updatePrice(bid, $('.rate-sell'));
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

        if (!$('.payment-preference-confirm').html().trim() && window.action == window.ACTION_BUY) {
            toggleBuyModal();
            return;
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
