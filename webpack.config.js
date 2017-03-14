var path = require('path');
var webpack = require('webpack');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
var OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin');
var BundleTracker = require('webpack-bundle-tracker');

module.exports = {
    context: __dirname,
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
    output: {
        path: path.resolve('./static/bundles/'),
        filename: "bundle.js",
    },
    plugins: [
        new BundleTracker({
            filename: './webpack-stats.json'
        }),
        new ExtractTextPlugin('bundle.css'),
        new OptimizeCssAssetsPlugin(),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.jQuery': 'jquery',
            'window.$': 'jquery',
            NProgress: 'nprogress',
            toastr: 'toastr',
            Cookies: 'js-cookie',
            moment: 'moment',
        }),
        new webpack.optimize.UglifyJsPlugin({
            sourceMap: true,
            compressor: {
                warnings: false
            }
        })
    ],
    watch: false,
    entry: [
        // npm js
        './node_modules/select2/dist/js/select2.full.js',
        './node_modules/jquery-ticker/jquery.ticker.js',
        './node_modules/card/dist/jquery.card.js',
        './node_modules/jquery-ui/ui/widgets/datepicker.js',
        './node_modules/js-cookie/src/js.cookie.js',
        './node_modules/moment-timezone/builds/moment-timezone-with-data.js',
        './node_modules/intl-tel-input/build/js/intlTelInput.js',
        './node_modules/bootstrap-toggle/js/bootstrap-toggle.min.js',
        // loader
        'bootstrap-loader',
        // run package
        './static/run.js',
        // old javascript
        './static/js/profile.js',
        './static/js/main.js',
        './static/js/index_orders.js',
        './static/js/footer.js',
        './static/js/django_jquery_csrf_setup.js'
    ]
};
