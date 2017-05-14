!(function (window, $) {
    'use strict';

    $(document).ajaxStart(function () {
        NProgress.start();
    });
    $(document).ajaxComplete(function () {
        setTimeout(function () {
            NProgress.done();
        }, 500);
    });
       var url = window.location.href,
           urlFragments = url.split('/'),
           pairPos = urlFragments.length - 2,
           pair = urlFragments[pairPos],
           currency = pair.substring(3, 6),
           currency_to = pair.substring(0, 3),
           currencyElem,
           paymentMethodsAccountEndpoint = '/en/paymentmethods/account/ajax/',
           cardsEndpoint = '/en/payments/options/',
           // Required modules

           orderObject = require('./modules/orders.js'),
           paymentObject = require('./modules/payment.js'),
           register = require('./modules/register.js'),
           captcha = require('./modules/captcha.js'),
           cryptoCurrCodes = ['BTC', 'ETH', 'LTC', 'RNS'],
           $currencyFrom,
           $currencyTo,
           $currencyPair,
           $currencySelect,
           phone,
           token,
           email,
           username,
           login_with_email,
           paymentFormRules = {
                'iban_holder': {
                    required: true,
                    iban: false
                },
                'email': {
                    email: true,
                    required: true
                },
               'acoount-number': {
                    number: true,
                    required: true
               },
               'acoount-bic': {
                    required: true,
                    bic: true
               }
            },
           paymentMessages = {
                'iban_holder': {
                    required: gettext('Account Holder is required')
                },
               'email': {
                    required: gettext('Account Email is required'),
                    email: gettext('Please enter a valid email')
               },
               'acoount-number': {
                    required: gettext('Account Number is required'),
                    number: gettext('Please enter a valid number (i.e. 123456)')
                },
               'acoount-bic': {
                    required: gettext('BIC/SWIFT is required'),
                    bic: gettext('Please enter a BIC/SWIFT (i.e. BELADEBEXXX)')
                }

           };

        $('.trade-type').val('1');

        window.ACTION_BUY = 1;
        window.ACTION_SELL = 0;
        window.action = window.ACTION_BUY; // 1 - BUY 0 - SELL

    $(function () {
        $(window).load(function() {
            $('body').fadeTo(1, 1000, function () {
                try {
                    orderObject.setCurrency(false, currency, currency_to, pair);
                    paymentObject.loadPaymentMethods(cardsEndpoint, currency);
                } catch (suppress) {}
            });
        });

        if( /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ) {
            $('.select2').removeClass('select2');
        } else {
            $(".select2").select2({'containerCssClass': 'currency-select ' +
            'currency-pair chart_panel_selectbox classic'});
        }


        if (currencyElem && currencyElem.val()){
                currency = currencyElem.val().toLowerCase();
        }

        $currencySelect = $('.currency-select');
        $currencyFrom = $('.currency-from');
        $currencyTo = $('.currency-to');
        $currencyPair = $("select[name='currency_pair']");
        $currencyFrom.val(currency);
        $currencyPair.val(pair).trigger('change.select2');
        $currencyTo.val(currency_to);
        var timer = null,
            delay = 500,
            phones = $('.phone'),
            verification_code = $('#verification_code');
        //if not used idx: remove jshint
        phones.each(function () {
            if(typeof $(this).intlTelInput === 'function') {
                // with AMD move to https://codepen.io/jackocnr/pen/RNVwPo
                $(this).intlTelInput();
                $(this).intlTelInput("setCountry", window.countryCode);
            }
        });
         var stripSpaces = function stripSpaces() {
            var val = $(this).val();
            val = val.split(' ').join('');
            $(this).val(val);
        };
        phones.on('keyup', stripSpaces);
        verification_code.on('keyup', stripSpaces);

        orderObject.updateOrder($('.amount-coin'), true, currency);
        // if not used event, isNext remove  jshint


        $('#graph-range').on('change', function() {
            orderObject.setCurrency(false, currency, currency_to, pair);
        });

        $('.exchange-sign').click(function () {
            var menuElem = $('.menu1');

            window.action = menuElem.hasClass('sell') ?
                window.ACTION_BUY : window.ACTION_SELL;

            orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    menuElem.toggleClass('sell');
            });
        });

        $('.trigger').click(function(){
            $('.trigger').removeClass('active-action');
            $(this).addClass('active-action');
            if ($(this).hasClass('trigger-buy')) {
                $('.menu1').removeClass('sell');
                window.action = window.ACTION_BUY;
                orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    if ((cryptoCurrCodes.indexOf($currencyFrom.val()) >= 0) && (cryptoCurrCodes.indexOf($currencyTo.val()) >= 0)) {
                        $('.payment-preference-confirm').text('EXCHANGE');
                        orderObject.changeState(null, 'next');
                    } else {
                        orderObject.toggleBuyModal();
                        $('.payment-fee').removeClass('hidden');
                    }

                });

            } else {
                $('.menu1').addClass('sell');
                window.action = window.ACTION_SELL;
                orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    if ((cryptoCurrCodes.indexOf($currencyFrom.val()) >= 0) && (cryptoCurrCodes.indexOf($currencyTo.val()) >= 0)) {
                        $('.payment-preference-confirm').text('EXCHANGE');
                        setTimeout(function () {
                            orderObject.changeState(null, 'next');
                        }, 600);
                    } else {
                        orderObject.toggleSellModal();
                    }
                });
            }

            $('.trade-type').val(window.action);

            orderObject.updateOrder($('.amount-coin'), true, currency);

            var newCashClass = window.action === window.ACTION_BUY ? 'rate-buy' : 'rate-sell';
              $('.amount-cash, .amount-coin')
                .removeClass('rate-buy')
                .removeClass('rate-sell')
                .addClass(newCashClass);
        });

        $('.amount').on('keyup', function () {
            // Protection against non-integers
            // TODO: export outside
            var val = this.value,
                lastChar = val.slice(-1),
                prevVal = val.substr(0, val.length-1);
            if(!!prevVal && lastChar === '.' &&
                prevVal.indexOf('.') === -1) {
                return;
                // # TODO: User isNaN
            } else if(!parseInt(lastChar) &&
                      parseInt(lastChar) !== 0) {
                // TODO: animate error
                $(this).val(prevVal);
                return;
            }
            var self = this,
                loaderElem = $('.exchange-sign'),
                cb = function animationCallback() {
                    loaderElem.one('animationiteration webkitAnimationIteration', function() {
                        loaderElem.removeClass('loading');
                    });

                    setTimeout(function () {
                        loaderElem.removeClass('loading');
                    }, 2000);// max animation duration
                };

            loaderElem.addClass('loading');
            if (timer) {
                clearTimeout(timer);
                timer = null;
            }
            timer = setTimeout(function () {
                orderObject.updateOrder($(self), false, currency, cb);
            }, delay);
        });

         $('.payment-method').on('change', function () {
            paymentObject.loadPaymentMethodsAccount(paymentMethodsAccountEndpoint);

        });

        $currencySelect.on('change', function () {
            if ($(this).hasClass('currency-pair')) {
                var selected = $(this).find('option:selected');
                currency = selected.attr('data-fiat');
                currency_to = selected.attr('data-crypto');
                pair = currency_to + currency;
            } else if ($(this).hasClass('currency-from')) {
                currency = $(this).val();
                currency_to = $('.currency-to').val();
                pair = currency_to + currency;
            } else if ($(this).hasClass('currency-to')) {
                currency_to = $(this).val();
                currency = $('.currency-from').val();
                pair = currency_to + currency;

            }
            orderObject.setCurrency($(this), currency, currency_to, pair);
            paymentObject.loadPaymentMethods(cardsEndpoint, currency);
            //bind all select boxes
            $currencyFrom.val(currency);
            $currencyPair.val(pair).trigger('change.select2');
            $currencyTo.val(currency_to);
            orderObject.updateOrder($('.amount-coin'), false, currency);
            // orderObject.reloadCardsPerCurrency(currency, cardsEndpoint);
        });
        //using this form because the object is inside a modal screen
        $(document).on('change','.payment-method', function () {
            var pm = $('.payment-method option:selected').val();
            $('#payment_method_id').val(pm);
            paymentObject.loadPaymentMethodsAccount(paymentMethodsAccountEndpoint, pm);

        });

    });

    $(function() {
        // For order index
        $('[data-toggle="popover"]').popover({content: $("#popover-template").html()});
        $( "#id_date" ).datepicker({ dateFormat: 'yy-mm-dd' });

        // TODO: get api root via DI
        $('#payment_method_id').val('');
        $('#user_address_id').val('');
        $('#new_user_account').val('');
        // TODO: if no amount coin selected DEFAULT_AMOUNT to confirm
        var amountCoin = $('.amount-coin'),
            confirm = amountCoin.val() ? amountCoin.val() : DEFAULT_AMOUNT;
        $('.btc-amount-confirm').text(confirm);


           var placerAjaxOrder = '/en/orders/add_order/',
            paymentAjax = '/en/payments/ajax/',
            DEFAULT_AMOUNT = 1;

        $('.next-step, .prev-step').on('click', orderObject.changeState);
        $('.phone.val').on('keyup', function () {
            if($(this).val().length) {
                $('.create-acc')
                    .not('.resend')
                    .removeClass('disabled');
            }
        });

        $('.email.val').on('keyup', function () {
            if($(this).val().length) {
                $('.create-acc')
                    .not('.resend')
                    .removeClass('disabled');
            }
        });

        $('.create-acc').on('click', function () {
            if ($(this).hasClass('disabled')) {
                return;
            }
            $('.switch-login').addClass('hidden');
            if ($('.send-otp').is(':visible') || $('.send').is(':visible')) {
                grecaptcha.execute();
            } else {
                window.submitCreateAcc();
            }
        });

        window.submitCreateAcc = function() {
            if ($('.email-verification').is(':visible')) {
                email = $('.register .email').val();
                login_with_email = true;
                phone = null;
            } else {
                login_with_email = false;
                email = null;
                phone = null;
                if ($('#login-form').is(':visible')) {
                    username = $('#id_username').val();
                    if (username.indexOf('@') !== -1) {
                        email = username;
                        login_with_email = true;
                    } else {
                        phone = username;
                    }

                } else {
                    phone = $('.register .phone').val();
                }
            }
            var regPayload = {
                phone: phone,
                email: email,
                login_with_email: login_with_email,
                g_recaptcha_response: grecaptcha.getResponse()
            };
            register.seemlessRegistration(regPayload);
        };

        $('.verify-acc').on('click', function () {
            if ($('.email-verification').is(':visible')) {
                email = $('.register .email').val();
                token = $('#verification_code').val();
                login_with_email = true;
                phone = null;
            } else {
                login_with_email = false;
                email = null;
                phone = null;
                if ($('#login-form').is(':visible')) {
                    token = $('#id_password').val();
                    username = $('#id_username').val();
                    if (username.indexOf('@') !== -1) {
                        email = username;
                        login_with_email = true;
                    } else {
                        phone = username;
                    }
                } else {
                    token = $('#verification_code').val();
                    phone = $('.register .phone').val();

                }
            }
            var verifyPayload = {
                token: token,
                phone: phone,
                email: email,
                login_with_email: login_with_email
            };
            register.verifyAccount(verifyPayload);
        });

        $('.switch-login').on('click', function () {
            if ($(this).hasClass('email-verification')) {
                $('.phone-verification').removeClass('hidden');
                $('.email-verification').addClass('hidden');
            } else {
                $('.email-verification').removeClass('hidden');
                $('.phone-verification').addClass('hidden');
            }
        });

        $('.place-order').on('click', function () {
            //TODO verify if $(this).hasClass('sell-go') add
            // the other type of transaction
            // add security checks
            var preferenceName = $('.payment-preference-confirm').text(),
                payment_preference = paymentObject.getPaymentPreference();
            if (preferenceName === 'EXCHANGE') {
                payment_preference = preferenceName;
            }

            var verifyPayload = {
                'trade-type': $('.trade-type').val(),
                'csrfmiddlewaretoken': $('#csrfmiddlewaretoken').val(),
                'amount-base': $('.amount-coin').val() || DEFAULT_AMOUNT,
                'currency_from': $('.currency-from').val(), //fiat
                'currency_to': $('.currency-to').val(), //crypto
                'payment_preference': payment_preference,
                '_locale': $('.topright_selectbox').val()
            };

            $.ajax({
                type: 'POST',
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
                    if (window.action == window.ACTION_BUY) {
                        $(document).trigger('nexchange.cc-form-load');
                        $("#pay-mastercard-form").card({
                            container: '.card-wrapper',

                            formSelectors: {
                                nameInput: 'input[name="firstname"], input[name="lastname"]',
                                numberInput: 'input#ccn',
                                expiryInput: 'input#ccexp',
                                cvcInput: 'input#cvv'
                            },
                            debug: false
                        });
                    }
                },
                error: function () {
                	var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });

        });



      $('.make-payment').on('click', function () {
            var verifyPayload = {
                'order_id': $('.trade-type').val(),
                'csrfmiddlewaretoken': $('#csrfmiddlewaretoken').val(),
                'amount-cash': $('.amount-cash').val(),
                'currency_from': $('.currency-from').val(),
            };

            $.ajax({
                type: 'post',
                url: paymentAjax,
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function (data) {
                    $('.paymentMethodsHead').addClass('hidden');
                    $('.paymentMethods').addClass('hidden');
                    $('.paymentSuccess').removeClass('hidden').html($(data));
                    $('.next-step').click();
                },
                error: function () {
                	var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });
        });

        $(document).on('click', '.buy .payment-type-trigger', function () {
            var paymentType = $(this).data('label'),
                actualPaymentType = $(this).data('type'),
                preferenceIdentifier = $(this).data('identifier'),
                preferenceFee = $(this).data('fee_deposit'),
                preferenceFeePercent = parseFloat(preferenceFee*100).toFixed(1),
                preferenceFeeAmount = parseFloat(preferenceFee * $('.cash-amount-confirm').text()).toFixed(2);
            paymentObject.setPaymentPreference({'method': actualPaymentType});
            $('.payment-preference-confirm').text(paymentType);
            $('.payment-preference-fee-percent').text(preferenceFeePercent);
            $('.payment-preference-fee-amount').text(preferenceFeeAmount);
            $('.payment-preference-actual').text(actualPaymentType);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);
            $(this).closest('.modal').modal('hide');
            $('.payment-method').val(paymentType);
            orderObject.changeState(null, 'next');
        });
        // $(document).on('click', '.payment-type-trigger-footer', paymentNegotiation);

        $(document).on('click', '.sell .payment-type-trigger', function () {
                var paymentType = $(this).data('type').toLocaleLowerCase(),
                modalId = paymentType + 'SellModal',
                modal = $('#' + modalId);
            $(this).closest('.modal').modal('hide');
            modal.modal('show');
        });

        $('.add_payout_method .back').click(function () {
            $(this).closest('.modal').modal('toggle');
            $('#sell_options_modal').modal('toggle');
        });

        $('.payment-widget .val').on('keyup, keydown', function() {
            var val = $(this).closest('.val');
            if (!val.val().length) {
               $(this).removeClass('error').removeClass('valid');
                return;
            }
           if (val.hasClass('jp-card-invalid')) {
                $(this).removeClass('valid').addClass('error');
                // $('.save-card').addClass('disabled');
            } else {
               $(this).removeClass('error').addClass('valid');
               // $('.save-card').removeClass('disabled');
           }

        });

        $('.card-form').each(function () {
            $(this).validate({rules: paymentFormRules, messages: paymentMessages});
        });

        $(document).on('nexchange.cc-form-load', function() {
            // TODO: add validation logic here
        });

        $(document).on('submit', '#pay-mastercard-form', function (event) {
            event.preventDefault();
            var verifyPayload = $(this).serialize();

            $.ajax({
                type: 'POST',
                url: '/en/payments/pay_with_credit_card/',
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function (data) {
                    //if the transaction is Buy
                    var message;
                    message = gettext('Order paid successfully');
                    toastr.success(message);
                    window.location.href = JSON.parse(data).redirect;

                },
                error: function (jqXHR) {
                    if (jqXHR.status == 403) {
                        toastr.error(jqXHR.responseText);
                    } else {
                        var message = gettext('Something went wrong. Please, try again.');
                        toastr.error(message);
                    }
                }
            });
        });

        $('.save-card').click(function() {
            var form = $(this).closest('.payment-widget').find('form'),
                valid = $(form).valid();
            if (valid) {
                submitSellPaymentPreference($(form));
            } else {
                var errorMsg = gettext('Please correct form errors and try again');
                toastr.error(errorMsg);
            }

        });

        $('.iban.account-number').on('change', function () {
            var elem = $(this).prev(),
                currentFlag = elem.data('flag');
            if ($(this).valid()) {
                var newFlag = $(this).val().substr(0,2).toLocaleLowerCase();
                elem
                    .removeClass(currentFlag)
                    .addClass(newFlag);
            }
        });
        function submitSellPaymentPreference (self) {
            $('.supporetd_payment').addClass('hidden');
            // TODO: Add handling for qiwi wallet with .intlTelInput('getNumber')
            if ($(self).hasClass('disabled')) {
                return false;
            }

            var form = $(self).closest('.modal-body'),
                preferenceElem = form.find('.account-number.val'),
                preferenceIdentifier = preferenceElem.val(),
                preferenceOwner = form.find('.iban.val').val(),
                bic = form.find('.acoount-bic').val(),
                method = form.find('.method').val();

            if (preferenceElem.hasClass('account-iban')) {
                if (!IBAN.isValid(preferenceIdentifier.val())) {
                    toastr.error('Invalid IBAN');
                    return false;
                }
            }

            if (window.action == window.ACTION_SELL){
                $('.buy-go').addClass('hidden');
                $('.sell-go').removeClass('hidden');
            }

            paymentObject.setPaymentPreference({
                'owner': preferenceOwner,
                'iban': preferenceIdentifier,
                'bic': bic,
                'method': method
            });
            $('.payment-preference-owner').val(preferenceOwner);
            $('.payment-preference-identifier').val(preferenceIdentifier);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);

            $(self).closest('.modal').modal('hide');

            setTimeout(function () {
                orderObject.changeState(null, 'next');
            }, 600);
        }
    });

    //for tests selenium
    function submit_phone(){
        var apiRoot = '/en/api/v1',
            menuEndpoint = apiRoot + '/menu',
            breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
            validatePhoneEndpoint = '/en/profile/verifyPhone/';
            var verifyPayload = {
                token: $('#verification_code').val(),
                phone: $('.register .phone').val()
            };
            $.ajax({
                type: 'POST',
                url: validatePhoneEndpoint,
                data: verifyPayload,
                success: function (data) {
                    if (data.status === 'OK') {
                        orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                        orderObject.changeState('next');
                    } else {
                	    var message = gettext('The code you sent was incorrect. Please, try again.');
                        toastr.error(message);
                    }
                },
                error: function () {
                	var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });

    }

    function payment_error(msg) {
        if (msg && msg.length) {
            toastr.error(msg);
        }
    }



    window.submit_phone=submit_phone;
} (window, window.jQuery)); //jshint ignore:line
