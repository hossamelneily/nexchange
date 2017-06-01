/*jshint esversion: 6 */

import highcharts from 'highcharts';
import highchartsMore from 'highcharts-more';
highchartsMore(highcharts);


!(function(window, $) {
    "use strict";

    var apiRoot = '/en/api/v1/price/',
        chartDataRaw;

    function responseToChart(data) {
        var i,
            resPair = [];
        for (i = 0; i < data.length; i += 2) {
            var price = data[i],
                ask = parseFloat(price.ticker.ask),
                bid = parseFloat(price.ticker.bid);
            resPair.push([Date.parse(price.created_on), ask, bid]);
        }
        return {
            pair: resPair
        };
    }

    function renderChart(pair, title, hours) {
        var tickerHistoryUrl = apiRoot + pair + '/history',
            tickerLatestUrl = apiRoot + pair + '/latest',
            data_points = window.innerWidth;
        if (hours) {
            tickerHistoryUrl = tickerHistoryUrl + '?hours=' + hours.replace(',', '.') + '&data_points=' + data_points;
        }
        else {
            tickerHistoryUrl = tickerHistoryUrl + '?data_points=' + data_points;
        }

        if ($('body').find('#container-graph').length > 0) {
            $.get(tickerHistoryUrl, function(resdata) {
                chartDataRaw = resdata;
                var data = responseToChart(resdata).pair,
                    container = $("#container-graph");
                highcharts.chart('container-graph', {
                    chart: {
                        type: 'arearange',
                        zoomType: 'x',
                        backgroundColor: '#F3F3F3'
                    },
                    style: {
                        fontFamily: 'Gotham'
                    },
                    credits: {
                        enabled: false
                   },
                    backgroundColor: {
                        linearGradient: {
                            x1: 0,
                            y1: 0,
                            x2: 1,
                            y2: 1
                        },
                        stops: [
                            [0, '#F3F3F3'],
                            [1, '#F3F3F3']
                        ]
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
                    events: {
                        load: function() {
                            // set up the updating of the chart each second
                            $('.highcharts-credits').remove();
                            var series = this.series[0],
                                interval = 10;
                            var intervalId = setInterval(function() {
                                if (pair != $('.currency-pair option:selected').val()) {
                                    clearInterval(intervalId);
                                } else {
                                    $.get(tickerLatestUrl, function(resdata) {
                                        var lastdata = responseToChart(resdata).pair,
                                            points = points || series.points;
                                        if (hours < 1) {
                                            // live mode
                                            var _lastadata = lastdata[0];
                                            if (_lastadata[1] >= _lastadata[2]) {
                                                var a = _lastadata[1];
                                                _lastadata[1] = _lastadata[2];
                                                _lastadata[2] = a;
                                            }
                                            series.addPoint(_lastadata, true, false, {
                                                duration: 500,
                                                easing: 'ease-in'
                                            });
                                            Array.prototype.push.apply(chartDataRaw, resdata);
                                        }
                                    });
                                }
                            }, interval * 1000);
                        }
                    },
                    series: [{
                        name: pair,
                        data: data,
                        color: '#8cc63f',
                        pointInterval: 1000
                    }]
                });
            });
        }
    }

    module.exports = {
        responseToChart: responseToChart,
        renderChart: renderChart,
        apiRoot: apiRoot,
        chartDataRaw: chartDataRaw
    };
}(window, window.jQuery)); //jshint ignore:line
