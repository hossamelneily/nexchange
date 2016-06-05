!(function (window, $) {
    var apiRoot = '/en/api/v1',
        tickerHistoryUrl = apiRoot +'/price/history',
        tickerLatestUrl = apiRoot + '/price/latest',
        currency = 'rub',
        animationDelay = 3000,
        chartDataRaw;
        $(".trade-type").val("1");


    window.ACTION_BUY = 1;
    window.ACTION_SELL = 0;
    window.action = ACTION_BUY; // 1 - BUY 0 - SELL

    $(function () {
            setCurrency();
            var timer = null,
                delay = 500;
            updateOrder($('.amount-coin'));
            
            $('.trigger').click( function(){
                $('.trigger').removeClass('active');
                $(this).addClass('active');
                if ($(this).hasClass('trigger-buy')) {
                    $('.buy-go').addClass('hidden');
                    $('.sell-go').removeClass('hidden');
                    window.action = window.ACTION_BUY;
                    $('.next-step').removeClass('btn-danger').addClass('btn-success');
                    $('.step4 i').removeClass('fa-btc').addClass('fa-money');
                    $('.step5 i').removeClass('fa-money').addClass('fa-btc');
                } else {
                    $('.sell-go').addClass('hidden');
                    $('.buy-go').removeClass('hidden');
                    window.action = window.ACTION_SELL;
                    $('.next-step').removeClass('btn-success').addClass('btn-danger');
                    $('.step4 i').removeClass('fa-money').addClass('fa-btc');
                    $('.step5 i').removeClass('fa-btc').addClass('fa-money');
                }

                $(".trade-type").val(window.action);

                updateOrder($('.amount-coin'));

                var newCashClass = action === window.ACTION_BUY ? 'rate-buy' : 'rate-sell';
                $('.amount-cash')
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

            $('.currency-select').on('change', function () {
                currency = $(this).val().toLowerCase();
                setCurrency();
                updateOrder($('.amount-coin'));
            });
        });



    function reonseToChart(data) {
        var i,
            resRub = [],
            resUsd = [];
        for (i = 0; i < data.length; i+=2) {
            var sell = data[i],
            buy = data[i + 1];
            resRub.push([sell['created_on'], buy['price_rub_formatted'], sell['price_rub_formatted']]);
            resUsd.push([sell['created_on'], buy['price_usd_formatted'], sell['price_usd_formatted']]);
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

    function renderChart () {
         $.get(tickerHistoryUrl, function(resdata) {
            chartDataRaw = resdata;
            var data = reonseToChart(resdata)[currency];
          $('#container').highcharts({

                chart: {
                    type: 'arearange',
                    zoomType: 'x',
                    events : {
                        load : function () {
                            // set up the updating of the chart each second
                            var series = this.series[0];
                            setInterval(function () {
                                $.get(tickerLatestUrl, function (resdata) {
                                    var lastdata = reonseToChart(resdata)[currency];
                                    if ( parseInt(resdata[0]["unix_time"]) >
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
                        day: '%b %e',
                        hour: '%b %e'
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
                    data: data
                }]
            });
        });
    }
} (window, window.jQuery));