var path = require('path');
var webpack = require('webpack');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
var OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin');


module.exports = {
    module: {
        loaders: [{
            loader: "babel-loader",
            include: [
                path.resolve(__dirname, "static/js"),
            ],
            test: /\.js?$/,
            query: {
                plugins: ['transform-runtime'],
                presets: ['es2015', 'stage-0', 'react'],
            },
        }, {
            test: /\.css$/,
            loader: ExtractTextPlugin.extract({
                fallback: 'style-loader',
                use: 'css-loader'
            })
        }, {
            test: /\.scss$/,
            loader: ExtractTextPlugin.extract({
                fallback: 'style-loader',
                use: 'css-loader'
            })
        }, {
            test: /\.(png|jpg|svg)?(\?v=\d+.\d+.\d+)?$/,
            loader: 'url-loader?limit=8192'
        }, {
            test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
            loader: 'url-loader?limit=10000&mimetype=application/font-woff'
        }, {
            test: /\.(ttf|otf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?|(jpg|gif)$/,
            loader: 'file-loader'
        }]
    },
    resolve: {
        alias: {
            modules: path.join(__dirname, "node_modules"),
        }
    },
    output: {
        path: './static/dist/css',
        filename: '../js/bundle.js'
    },
    plugins: [
        new ExtractTextPlugin('bundle.css'),
        new OptimizeCssAssetsPlugin(),
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "window.jQuery": "jquery",
            "window.$": "jquery",
            highcharts: 'highcharts',
            NProgress: 'nprogress'
        }),
        new webpack.optimize.UglifyJsPlugin({
            compressor: {
                warnings: false
            }
        })
    ],
    watch: false,
    entry: [
        'babel-polyfill',
        'bootstrap-loader',
        // npm js
        './node_modules/select2/dist/js/select2.full.js',
        './node_modules/jquery-ticker/jquery.ticker.js',
        // run package
        './static/run.js',
        // old javascript
        './static/js/add_orders.js',
        './static/js/profile.js',
        './static/js/main.js',
        './static/js/index_orders.js',
        './static/js/footer.js',
        './static/js/django_jquery_csrf_setup.js'
    ]
};
