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
                    $(this).intlTelInput();
                }
            });
            updateOrder($('.amount-coin'));
            
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
                setCurrency();
                updateOrder($('.amount-coin'));
            });
            //using this form because the object is inside a modal screen
            $(document).on('change','.payment-method', function () {
                var pm = $('.payment-method option:selected').val();
                $('#payment_method_id').val(pm);
                loadPaymenMethodsAccount(paymentMethodsAccountEndpoint,pm);

            });

        });



    function reonseToChart(data) {
        var i,
            resRub = [],
            resUsd = [];
        for (i = 0; i < data.length; i+=2) {
            var sell = data[i],
            buy = data[i + 1];
            resRub.push([Date.parse(sell['created_on']), buy['price_rub_formatted'], sell['price_rub_formatted']]);
            resUsd.push([Date.parse(sell['created_on']), buy['price_usd_formatted'], sell['price_usd_formatted']]);
        }

        return {
            rub: resRub,
            usd: resUsd
        }
    }

    function updateOrder (elem) {
        var val,
            rate,
            floor = 100000000;

        val = parseFloat(elem.val());

        if (!val) {
            return;
        }

        $.get(tickerLatestUrl, function(data) {
            updatePrice(getPrice(data[ACTION_BUY]), $('.rate-buy'));
            updatePrice(getPrice(data[ACTION_SELL]), $('.rate-sell'));
            rate = data[action]['price_' + currency + '_formatted'];
            if (elem.hasClass('amount-coin')) {
                var cashAmount = rate * val;
                $('.amount-cash').val(cashAmount);
            } else {
                var btcAmount = Math.floor(val / rate * floor) / floor;
                $('.amount-coin').val(btcAmount);
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
        isReasonableChange = price < currentPrice * 2;
        if (currentPrice < price && isReasonableChange) {
            animatePrice(price, elem, true);
        }
        else if (!isReasonableChange) {
            setPrice(elem, price);
        }

        isReasonableChange = price * 2 > currentPrice;
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

    function setCurrency () {   
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
        data = {'payment_method': pm}
        $.get(paymentMethodsAccountEndpoint, data,function (data) {
            $(".paymentMethodsAccount").html($(data));
        });
        $('.paymentMethodsAccount').removeClass('hidden');
    }

    function renderChart () {
         $.get(tickerHistoryUrl, function(resdata) {
            chartDataRaw = resdata;
            
            var data = reonseToChart(resdata)[currency];
            
            // Data for testing porpuse
            // data = [[Date.parse("2016-07-20T20:06:01.394842"), 410.16505167880126, 745.4641755838375], [Date.parse("2016-07-20T20:11:01.394842"), 429.7037130019566, 763.1052344875606], [Date.parse("2016-07-20T20:16:01.394842"), 452.5781250238309, 780.3095088711442], [Date.parse("2016-07-20T20:21:01.394842"), 495.15312467289516, 782.3227860922436], [Date.parse("2016-07-20T20:26:01.394842"), 480.60296114226367, 776.9961597528744], [Date.parse("2016-07-20T20:31:01.394842"), 495.72256409232466, 776.6642558791378], [Date.parse("2016-07-20T20:36:01.394842"), 455.03627633803103, 751.4551288999572], [Date.parse("2016-07-20T20:41:01.394842"), 470.0603622889281, 716.3531779863628], [Date.parse("2016-07-20T20:46:01.394842"), 442.09522695964154, 704.1684704863433], [Date.parse("2016-07-20T20:51:01.394842"), 465.1486545724596, 720.3326436481407], [Date.parse("2016-07-20T20:56:01.394842"), 426.4003539589192, 796.1760949704016], [Date.parse("2016-07-20T21:01:01.394842"), 428.74047413763395, 787.7213747642262], [Date.parse("2016-07-20T21:06:01.394842"), 498.5016403308229, 769.8160900354151], [Date.parse("2016-07-20T21:11:01.394842"), 410.7133419141915, 710.2090054926603], [Date.parse("2016-07-20T21:16:01.394842"), 426.2857499960651, 733.0948429634601], [Date.parse("2016-07-20T21:21:01.394842"), 450.816941699352, 750.28143026262], [Date.parse("2016-07-20T21:26:01.394842"), 489.72112184121727, 710.9276388889303], [Date.parse("2016-07-20T21:31:01.394842"), 468.3828632956182, 733.0224099319817], [Date.parse("2016-07-20T21:36:01.394842"), 489.6417570680409, 736.4233402495819], [Date.parse("2016-07-20T21:41:01.394842"), 432.2874831789607, 749.2579525854425], [Date.parse("2016-07-20T21:46:01.394842"), 419.35321488035015, 723.0569476415943], [Date.parse("2016-07-20T21:51:01.394842"), 480.6234610163332, 742.7770190254505], [Date.parse("2016-07-20T21:56:01.394842"), 450.49163130289674, 747.7925911329843], [Date.parse("2016-07-20T22:01:01.394842"), 474.3828424540348, 793.5125173951848], [Date.parse("2016-07-20T22:06:01.394842"), 424.38975908656903, 770.9399939038935], [Date.parse("2016-07-20T22:11:01.394842"), 498.25420028099586, 723.1471499964362], [Date.parse("2016-07-20T22:16:01.394842"), 409.38387002217934, 752.0666383299156], [Date.parse("2016-07-20T22:21:01.394842"), 487.6800241052865, 763.4388880162278], [Date.parse("2016-07-20T22:26:01.394842"), 412.8476572160173, 752.9196889085986], [Date.parse("2016-07-20T22:31:01.394842"), 480.71163023729935, 728.721774562599], [Date.parse("2016-07-20T22:36:01.394842"), 462.2135826108696, 785.209670151761], [Date.parse("2016-07-20T22:41:01.394842"), 419.12311828005585, 788.069410897642], [Date.parse("2016-07-20T22:46:01.394842"), 462.93811586054267, 738.7987231477475], [Date.parse("2016-07-20T22:51:01.394842"), 439.60557719189364, 728.2849712306061], [Date.parse("2016-07-20T22:56:01.394842"), 442.30353032358875, 731.2583853724635], [Date.parse("2016-07-20T23:01:01.394842"), 430.19096533835574, 771.1277431492507], [Date.parse("2016-07-20T23:06:01.394842"), 431.03620382514447, 798.0742348989165], [Date.parse("2016-07-20T23:11:01.394842"), 435.6885535700948, 733.4374780098658], [Date.parse("2016-07-20T23:16:01.394842"), 486.656418396134, 708.3278495202973], [Date.parse("2016-07-20T23:21:01.394842"), 481.4294749457056, 786.0045592107824], [Date.parse("2016-07-20T23:26:01.394842"), 469.0856929882874, 798.6055538779726], [Date.parse("2016-07-20T23:31:01.394842"), 457.34273585534976, 728.5690955726379], [Date.parse("2016-07-20T23:36:01.394842"), 408.6949966044121, 706.6908484865352], [Date.parse("2016-07-20T23:41:01.394842"), 489.0606275796455, 740.8431373126381], [Date.parse("2016-07-20T23:46:01.394842"), 438.7945600052761, 791.2878882598117], [Date.parse("2016-07-20T23:51:01.394842"), 425.3480037402282, 775.4952927662489], [Date.parse("2016-07-20T23:56:01.394842"), 438.180102181404, 761.9434971196888], [Date.parse("2016-07-21T00:01:01.394842"), 497.4094558423235, 751.4479508487069], [Date.parse("2016-07-21T00:06:01.394842"), 418.7808135177931, 703.5026162309155]]
            //
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
                                    var lastdata = reonseToChart(resdata)[currency];
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
