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
           currencyPos = urlFragments.length - 2,
           currency = urlFragments[currencyPos].toLowerCase(),
           currencyElem,
           paymentMethodsAccountEndpoint = '/en/paymentmethods/account/ajax/',
           cardsEndpoint = '/en/payments/options/',
           // Required modules
           orderObject = require('./modules/orders.js'),
           paymentObject = require('./modules/payment.js'),
           captcha = require('./modules/captcha.js'),
           $currencySelect;

        $('.trade-type').val('1');

        window.ACTION_BUY = 1;
        window.ACTION_SELL = 0;
        window.action = window.ACTION_BUY; // 1 - BUY 0 - SELL

    $(function () {
        if (currencyElem && currencyElem.val()){
                currency = currencyElem.val().toLowerCase();
        }

        $currencySelect = $('.currency-select');
        orderObject.setCurrency(false, currency);
        paymentObject.loadPaymentMethods(cardsEndpoint, currency);
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
            orderObject.setCurrency(false, currency);
        });

        $('.exchange-sign').click(function () {
            var menuElem = $('.menu1');

            window.action = menuElem.hasClass('sell') ?
                window.ACTION_BUY : window.ACTION_SELL;

            orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    menuElem.toggleClass('sell');
            });
        });

        $('.trigger').click( function(){
            $('.trigger').removeClass('active-action');
            $(this).addClass('active-action');
            if ($(this).hasClass('trigger-buy')) {
                $('.menu1').removeClass('sell');
                window.action = window.ACTION_BUY;
                orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    orderObject.toggleBuyModal();
                });

            } else {
                $('.menu1').addClass('sell');
                window.action = window.ACTION_SELL;
                orderObject.updateOrder($('.amount-coin'), false, currency, function () {
                    orderObject.toggleSellModal();
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
            currency = $(this).val().toLowerCase();
            orderObject.setCurrency($(this), currency);
            paymentObject.loadPaymentMethods(cardsEndpoint ,currency);
            //bind all select boxes
            $currencySelect.not('.currency-to').val($(this).val());
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
        function lockoutResponse (data) {
            var formattedTime = data
                    .responseJSON
                    .cooloff_time
                    .replace("PT","")
                    .replace("H",":")
                    .replace("M","")
                    .replace("S",""),
                errorMsg = gettext('You were locked out, please try again in '),
                completeMsg = errorMsg +
                    formattedTime + ' ' +
                    gettext('minutes');
            toastr.error(completeMsg);
        }

        function failureResponse (data, defaultMsg) {
            var _defaultMsg = gettext(defaultMsg),
                message = data.responseJSON.message || _defaultMsg;
            toastr.error(message);

        }

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

        var apiRoot = '/en/api/v1',
            createAccEndpoint =  '/en/accounts/authenticate/',
            menuEndpoint = apiRoot + '/menu',
            breadcrumbsEndpoint = apiRoot + '/breadcrumbs',
            validatePhoneEndpoint = '/en/accounts/verify_phone/',
            placerAjaxOrder = '/en/orders/add_order/',
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
        $('.create-acc').on('click', function () {
            if($(this).hasClass('disabled')) {
                return;
            }
            $('.phone.val').addClass('disabled');


            var regPayload = {
                // TODO: check collision with qiwi wallet
                phone: $('.register .phone').val(),
                g_recaptcha_response: grecaptcha.getResponse(),
            };
            $.ajax({
                type: 'POST',
                dataType: 'json',
                url: createAccEndpoint,
                data: regPayload,
                statusCode: {
                    200: function (data) {
                        $('.register .step2').removeClass('hidden');
                        $('.verify-acc').removeClass('hidden');
                        $('.create-acc').addClass('hidden');
                        $('.create-acc.resend').removeClass('hidden');
                    },
                    400: function (data) {
                        return failureResponse(
                            data,
                            'Invalid phone number'
                        );
                    },
                    403: lockoutResponse,
                    428: function (data) {
                        return failureResponse(
                            data,
                            'Invalid phone number'
                        );
                    }
                }
            });
        });

        $('.verify-acc').on('click', function () {
            var verifyPayload = {
                token: $('#verification_code').val(),
                phone: $('.register .phone').val()
            };
            $.ajax({
                type: 'POST',
                dataType: 'json',
                url: validatePhoneEndpoint,
                data: verifyPayload,
                statusCode: {
                    201: function(data) {
                        orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                        orderObject.changeState(null, 'next');
                    },
                    400: function (data) {
                        failureResponse(
                            data,
                            'Incorrect code'
                        );
                    },
                    403: lockoutResponse
                }
            });

        });


        $('.place-order').on('click', function () {
            //TODO verify if $(this).hasClass('sell-go') add
            // the other type of transaction
            // add security checks
            var actualPaymentType = $('.payment-preference-actual').text(),
                preferenceIdentifier = $('.payment-preference-identifier-confirm').text(),
                preferenceOwner = $('.payment-preference-owner-confirm').text(),
                verifyPayload = {
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
            preferenceIdentifier = $(this).data('identifier');
            $('.payment-preference-confirm').text(paymentType);
            $('.payment-preference-actual').text(actualPaymentType);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);
            $('#PayMethModal').modal('toggle');
            $('.payment-method').val(paymentType);
            orderObject.changeState(null, 'next');
        });
        // $(document).on('click', '.payment-type-trigger-footer', paymentNegotiation);

        $('.sell .payment-type-trigger').on('click', function () {
            var paymentType = $(this).data('type').toLocaleLowerCase(),
                modalId = paymentType + 'SellModal',
                modal = $('#' + modalId);
            $(this).closest('.modal').modal('hide');
            modal.modal('show');
        });

        $('.sellMethModal .back').click(function () {
            $(this).closest('.modal').modal('toggle');
            $('#UserAccountModal').modal('toggle');
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

        $('.payment-widget .save-card').on('click', function () {
            $('.supporetd_payment').addClass('hidden');
            // TODO: Add handling for qiwi wallet with .intlTelInput('getNumber')
            if ($(this).hasClass('disabled')) {
                return false;
            }

            var form = $(this).closest('.modal-body'),
                preferenceIdentifier = form.find('.val').val(),
                preferenceOwner = form.find('.name').val();

            $('.payment-preference-owner').val(preferenceOwner);
            $('.payment-preference-identifier').val(preferenceIdentifier);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);

            $(this).closest('.modal').modal('hide');
            
            setTimeout(function () {
                orderObject.changeState(null, 'next');
            }, 600);
        });
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

    window.submit_phone=submit_phone;
} (window, window.jQuery)); //jshint ignore:line


