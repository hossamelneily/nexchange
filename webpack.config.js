var path = require('path');
var webpack = require('webpack');
var ExtractTextPlugin = require('extract-text-webpack-plugin');

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
            test: /\.(png|jpg|svg)?(\?v=\d+.\d+.\d+)?$/,
            loader: 'url-loader?limit=8192'
        },{
            test: /\.(eot|ttf|otf|woff|woff2)$/,
            loader: 'file-loader?minetype=application/font-woff'
        }]
    },
    output: {
        path: './static/dist/css',
        filename: '../js/bundle.js'
    },
    plugins: [
        new ExtractTextPlugin({
            filename: 'bundle.css',
            allChunks: true
        }),
        new webpack.ProvidePlugin({
          $: "jquery",
          jQuery: "jquery",
          "window.jQuery": "jquery"
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
        './static/index.js'
    ]
};
