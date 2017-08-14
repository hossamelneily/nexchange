import Extractor from '../helpers/Extractor.js';
import Animator from '../helpers/Animator.js';
import Notifier from '../helpers/Notifier.js';
import AccountCheck from '../authentication/AccountCheck.js';

const accountCheck = new AccountCheck();

class FlipSendWidget {
	constructor() {
		this.chartObject = require("../chart.js");
		this.verificationEndpoint = '/en/accounts/verify_user/';
		this.decimalPoints = 2;
		this.initCurrencySelect();
		this.initExchangeSign();

        let url = window.location.href,
			urlFragments = url.split('/'),
			pairPos = urlFragments.length - 2,
			pair = urlFragments[pairPos],
			currencyFrom = pair.substring(3, 6),
			currencyTo = pair.substring(0, 3);

        $('.currency-from').val(currencyFrom); 
        $('.currency-to').val(currencyTo);

		this.setCurrency(pair);
	}

	updateOrder($elUpdated, cb) {
		let $amountDeposit = $('#amount-deposit'),
			base = $('.currency-to').val(),
			quote = $('.currency-from').val(),
			pair = `${base}${quote}`;

		Animator.animateExchangeSign();

		$.get(`/en/api/v1/price/${pair}/latest`, (data) => {
			if (data.length == 0) return;

			// TODO: protect against NaN
			let rate = parseFloat(data[0].ticker.ask);

			if ($elUpdated.attr('id') == 'amount-receive')
				this.setAmountDeposit(rate);
			else
				this.setAmountReceive(rate);

			this.isMinimalAmountExceeded();

			if (cb) cb();
		});
	}

    getDecimalPlaces (amount) {
        let decimalPlaces = 2,
            invertedDecimalSize = -Math.floor(Math.log10(amount));

        if (invertedDecimalSize > 0)
            decimalPlaces = decimalPlaces + invertedDecimalSize;

        return decimalPlaces;
    }

	setAmountReceive(rate) {
		let amountDeposit = parseFloat($('#amount-deposit').val()),
			amountReceive = amountDeposit / rate,
			decimalPoints = this.getDecimalPlaces(amountReceive);

		$('#amount-receive').val(amountReceive.toFixed(decimalPoints));
	}

	setAmountDeposit(rate) {
		let amountReceive = parseFloat($('#amount-receive').val()),
			amountDeposit = amountReceive * rate,
			decimalPoints = this.getDecimalPlaces(amountDeposit);

		$('#amount-deposit').val(amountDeposit.toFixed(decimalPoints));
	}

	changeState(e, action) {
		if (e) e.preventDefault();
		if ($(this).hasClass('disabled')) return;

		let depositConfirm = `
			<span class="quote-amount-confirm">${$('#amount-deposit').val()}</span>
			<span class="currency">${$('#currency-from option:selected').val()}</span>`;

		let receiveConfirm = `
			<span class="base-amount-confirm">${$('#amount-receive').val()}</span>
			<span class="currency_base">${$('#currency-to option:selected').val()}</span>`;

		$('#deposit-amount-confirm').html(depositConfirm);
		$('#receive-amount-confirm').html(receiveConfirm);

		var paneClass = '.tab-pane',
			tab = $('.tab-pane.active'),
			action = action || $(this).hasClass('next-step') ? 'next' : 'prev', // jshint ignore:line
			nextStateId = tab[action](paneClass).attr('id'),
			nextState = $('[href="#' + nextStateId + '"]'),
			nextStateTrigger = $('#' + nextStateId),
			menuPrefix = "menu",
			numericId = parseInt(nextStateId.replace(menuPrefix, '')),
			currStateId = menuPrefix + (numericId - 1),
			currState = $('[href="#' + currStateId + '"]');

		//skip disabled state, check if at the end
		if (nextState.hasClass('disabled') &&
			numericId < $(".process-step").length &&
			numericId > 1) {
			this.changeState(null, action);
		}

		if (nextStateTrigger.hasClass('hidden')) {
			nextStateTrigger.removeClass('hidden');
		}

		if (!accountCheck.canProceedtoRegister(currStateId)) {
			$('.trigger-buy').trigger('click', true);
		} else {
			currState.addClass('completed');
			nextState.tab('show');
			window.scrollTo(0, 0);
		}

		$(window).trigger('resize');
	}

	isMinimalAmountExceeded() {
		let currentAmount = parseFloat($('#amount-receive').val()),
			minimumAmount = parseFloat($('#currency-to').find('option:selected').attr('data-minimal-amount'));

		if (currentAmount < minimumAmount) {
			let message = gettext(`Minimal order amount is ${minimumAmount} Coins`);
			toastr.error(message);

			$('#amount-receive').val(minimumAmount);
			this.updateOrder($('#amount-receive'));
		}
	}

    setCurrency(pair) {
		let reversePair = Extractor.reversePair(pair),
			title = Extractor.getTitleFromPair(reversePair);

		this.chartObject.renderChart(reversePair, title, $("#graph-range").val());
		this.updateOrder($('#amount-receive'));
    }

	initCurrencySelect() {
		let currencyFrom = $('.currency-from').val(),
			currencyTo = $('.currency-to').val(),
			pair;

        $('.currency-select').on('change', (e) => {
			let newCurrencyFrom = $('.currency-from').val(),
				newCurrencyTo = $('.currency-to').val();

        	if (newCurrencyFrom == newCurrencyTo) {
        		Notifier.failureResponse(null, 'Deposit and receive currencies cannot be the same.');
	        	$('.currency-from').val(currencyFrom);
	        	$('.currency-to').val(currencyTo);
        		return;
        	}

        	currencyFrom = $('.currency-from').val();
        	currencyTo = $('.currency-to').val();
        	pair = $('.currency-to').val() + $('.currency-from').val();

            this.setCurrency(pair);
        });
	}

	initExchangeSign() {
		$('#exchange-sign').click((e) => {
			Animator.animateExchangeSign();

			let pair = $('#currency-from option:selected').val() + $('#currency-to option:selected').val(),
				currencies = Extractor.getCurrenciesFromPair(pair),
				newPair = currencies[1] + currencies[0];

			$('.currency-from').val(currencies[1]);
			$('.currency-to').val(currencies[0]);

			this.setCurrency(pair);
		});
	}
}

export default new FlipSendWidget();