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
            floor = 100000000,
            floorCash = 1000,
            cashAmount,
            btcAmount;

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
                cashAmount = Math.floor(val * rate * floorCash) / floorCash;
                btcAmount = val;
                if (isInitial) {
                    $('.amount-cash').attr('placeholder', cashAmount);
                } else {
                    $('.amount-cash').val(cashAmount);
                }

            } else {
                btcAmount = Math.floor(val / rate * floor) / floor;
                cashAmount = val;

                if (isInitial) {
                    $('.amount-coin').attr('placeholder', btcAmount);
                } else {
                    $('.amount-coin').val(btcAmount);
                }
            }
            $('.btc-amount-confirm').text(btcAmount); // add
            $('.cash-amount-confirm').text(cashAmount); //add
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

    function setCurrency (elem, currency) {if (elem && elem.hasClass('currency_pair')) {
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

    module.exports = {
        updateOrder: updateOrder,
        updatePrice: updatePrice,
        animatePrice: animatePrice,
        getPrice: getPrice,
        setCurrency: setCurrency,
        setPrice: setPrice,
        setButtonDefaultState: setButtonDefaultState,
        changeState: changeState,
        reloadRoleRelatedElements: reloadRoleRelatedElements
    };
}(window, window.jQuery)); //jshint ignore:line



