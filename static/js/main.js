/*jshint esversion: 6 */

import InputsHelper from './modules/helpers/InputsHelper.js';

import accountCreation from './modules/authentication/AccountCreation.js';
import accountVerification from './modules/authentication/AccountVerification.js';

!(function(window, $) {
    'use strict';

    // Activate Bootstrap tooltips
    $(function() {
        $('[data-toggle="tooltip"]').tooltip();
    });

    $(document).ajaxStart(function() {
        NProgress.start();
    });

    $(document).ajaxComplete(function() {
        setTimeout(function() {
            NProgress.done();
        }, 500);
    });
    
    var paymentMethodsAccountEndpoint = '/en/paymentmethods/account/ajax/',
        cardsEndpoint = '/en/payments/options/',
        // Required modules
        paymentObject = require('./modules/payment.js'),
        captcha = require('./modules/captcha.js'),
        cryptoCurrCodes = ['BTC', 'ETH', 'LTC', 'RNS'],
        pairOption,
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

    $(function() {
        $(window).load(function() {
            $('body').fadeTo(1, 1000, function() {
                try {
                    paymentObject.loadPaymentMethods(cardsEndpoint, currency);
                } catch (suppress) {}
            });
        });

        var timer = null,
            delay = 500,
            phones = $('.phone');

        phones.each(function() {
            if (typeof $(this).intlTelInput === 'function') {
                $(this).intlTelInput();
                $(this).intlTelInput("setCountry", window.countryCode);
            }
        });
        phones.on('keyup', InputsHelper.stripSpaces);


        $('#graph-range').on('change', function() {
            let pair = $('.currency-to').val() + $('.currency-from').val();
        });

        $('.trigger').click(function() {
            $('.trigger').removeClass('active-action');
            $(this).addClass('active-action');

        });

        $('.amount').on('keyup', function() {
            // Protection against non-integers
            // TODO: export outside
            var val = this.value,
                lastChar = val.slice(-1),
                prevVal = val.substr(0, val.length - 1);
            if (!!prevVal && lastChar === '.' &&
                prevVal.indexOf('.') === -1) {
                return;
                // # TODO: User isNaN
            } else if (!parseInt(lastChar) &&
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

                    setTimeout(function() {
                        loaderElem.removeClass('loading');
                    }, 2000); // max animation duration
                };

            loaderElem.addClass('loading');
            if (timer) {
                clearTimeout(timer);
                timer = null;
            }
        });

        $('.payment-method').on('change', function() {
            paymentObject.loadPaymentMethodsAccount(paymentMethodsAccountEndpoint);
        });

        //using this form because the object is inside a modal screen
        $(document).on('change', '.payment-method', function() {
            var pm = $('.payment-method option:selected').val();
            $('#payment_method_id').val(pm);
            paymentObject.loadPaymentMethodsAccount(paymentMethodsAccountEndpoint, pm);

        });
    });

    $(function() {
        // For order index
        $('[data-toggle="popover"]').popover({
            content: $("#popover-template").html()
        });


        // TODO: get api root via DI
        $('#payment_method_id').val('');
        $('#user_address_id').val('');
        $('#new_user_account').val('');
        // TODO: if no amount coin selected DEFAULT_AMOUNT to confirm

        $('.base-amount-confirm').text(confirm);

        var placerAjaxOrder = '/en/orders/add_order/',
            paymentAjax = '/en/payments/ajax/',
            DEFAULT_AMOUNT = 1;


        $('.create-anonymous-acc').on('click', function() {
            if ($(this).hasClass('disabled')) {
                return;
            }
            $('.switch-login').addClass('hidden');
            accountCreation.createAnonymousAccount();
        });

        function sleep(time) {
            return new Promise((resolve) => setTimeout(resolve, time));
        }

        $("#user-login-key").bind('copy', function() {
            $('.verify-anonymous').prop('disabled', false);
            toastr.success(msg);
            sleep(500).then(() => {
                $('.hide-key').click();
            });
        });

        $('.show-hide-key').on('click', function() {
            if ($(this).hasClass('fa-eye')) {
                $(this).addClass('fa-eye-slash');
                $(this).removeClass('fa-eye');
                $('#user-login-key').attr('type', 'password');
            } else {
                $(this).addClass('fa-eye');
                $(this).removeClass('fa-eye-slash');
                $('#user-login-key').attr('type', 'text');
            }
        });

        $('.verify-anonymous').on('click', () => {
            accountVerification.verifyAnonymous();
        });

        $('.place-order').on('click', function() {
            // TODO verify if $(this).hasClass('sell-go') add
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
                success: function(data) {
                    var message;
                    if (window.action == window.ACTION_BUY) {
                        message = gettext('Buy order placed successfully');
                    } else {
                        message = gettext('Sell order placed successfully');
                    }

                    toastr.success(message);
                    $('.successOrder').html($(data));
                    $('#orderSuccessModal').modal({
                        backdrop: 'static'
                    });
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
                error: function() {
                    var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });

        });



        $('.make-payment').on('click', function() {
            var verifyPayload = {
                'order_id': $('.trade-type').val(),
                'csrfmiddlewaretoken': $('#csrfmiddlewaretoken').val(),
                'amount-cash': $('#amount-deposit').val(),
                'currency_from': $('.currency-from').val(),
            };

            $.ajax({
                type: 'post',
                url: paymentAjax,
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function(data) {
                    $('.paymentMethodsHead').addClass('hidden');
                    $('.paymentMethods').addClass('hidden');
                    $('.paymentSuccess').removeClass('hidden').html($(data));
                },
                error: function() {
                    var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });
        });

        $(document).on('click', '.buy .payment-type-trigger', function() {
            var paymentType = $(this).data('label'),
                actualPaymentType = $(this).data('type'),
                preferenceIdentifier = $(this).data('identifier'),
                preferenceFee = $(this).data('fee_deposit'),
                preferenceFeePercent = parseFloat(preferenceFee * 100).toFixed(1),
                preferenceFeeAmount = parseFloat(preferenceFee * $('.quote-amount-confirm').text()).toFixed(2);
            paymentObject.setPaymentPreference({
                'method': actualPaymentType
            });
            $('.payment-preference-confirm').text(paymentType);
            $('.payment-preference-fee-percent').text(preferenceFeePercent);
            $('.payment-preference-fee-amount').text(preferenceFeeAmount);
            $('.payment-preference-actual').text(actualPaymentType);
            $('.payment-preference-identifier-confirm').text(preferenceIdentifier);
            $(this).closest('.modal').modal('hide');
            $('.payment-method').val(paymentType);
        });

        $(document).on('click', '.sell .payment-type-trigger', function() {
            var paymentType = $(this).data('type').toLocaleLowerCase(),
                modalId = paymentType + 'SellModal',
                modal = $('#' + modalId);
            $(this).closest('.modal').modal('hide');
            modal.modal('show');
        });

        $('.add_payout_method .back').click(function() {
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
            } else {
                $(this).removeClass('error').addClass('valid');
            }
        });

        $('.card-form').each(function() {
            $(this).validate({
                rules: paymentFormRules,
                messages: paymentMessages
            });
        });

        $(document).on('submit', '#pay-mastercard-form', function(event) {
            event.preventDefault();
            var verifyPayload = $(this).serialize();

            $.ajax({
                type: 'POST',
                url: '/en/payments/pay_with_credit_card/',
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function(data) {
                    //if the transaction is Buy
                    var message;
                    message = gettext('Order paid successfully');
                    toastr.success(message);
                    window.location.href = JSON.parse(data).redirect;

                },
                error: function(jqXHR) {
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

        $('.iban.account-number').on('change', function() {
            var elem = $(this).prev(),
                currentFlag = elem.data('flag');
            if ($(this).valid()) {
                var newFlag = $(this).val().substr(0, 2).toLocaleLowerCase();
                elem
                    .removeClass(currentFlag)
                    .addClass(newFlag);
            }
        });

        function submitSellPaymentPreference(self) {
            $('.supporetd_payment').addClass('hidden');
            // TODO: Add handling for qiwi wallet with .intlTelInput('getNumber')
            if ($(self).hasClass('disabled')) {
                return false;
            }

            var form = $(self).closest('.modal-body'),
                method = form.find('.method').val(),
                preferenceElem,
                preferenceIdentifier,
                preferenceOwner,
                bic = form.find('.acoount-bic').val();
            if (method === 'qiwi') {
                preferenceElem = form.find('.phone.val');
                preferenceOwner = form.find('.iban.val').val();
            } else if (method === 'c2c') {
                preferenceElem = form.find('.account-number.val');
                preferenceOwner = form.find('.owner.val').val();
            } else {
                preferenceElem = form.find('.account-number.val');
                preferenceOwner = form.find('.iban.val').val();
            }
            preferenceIdentifier = preferenceElem.val();

            if (preferenceElem.hasClass('account-iban')) {
                if (!IBAN.isValid(preferenceIdentifier.val())) {
                    toastr.error('Invalid IBAN');
                    return false;
                }
            }

            if (window.action == window.ACTION_SELL) {
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

        }
    });

    //for tests selenium
    function submit_phone() {
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
            success: function(data) {
                if (data.status === 'OK') {
                    orderObject.reloadRoleRelatedElements(menuEndpoint, breadcrumbsEndpoint);
                } else {
                    var message = gettext('The code you sent was incorrect. Please, try again.');
                    toastr.error(message);
                }
            },
            error: function() {
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

    window.submit_phone = submit_phone;
}(window, window.jQuery)); //jshint ignore:line