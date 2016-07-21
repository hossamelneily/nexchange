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
                $('.currency-select').val($(this).val());
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
