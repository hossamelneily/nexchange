from django.conf import settings
from celery import shared_task

from risk_management.decorators import get_task
from risk_management.tasks.generic.account_balance_checker import \
    AccountBalanceChecker
from risk_management.tasks.generic.reserve_balance_checker import \
    ReserveBalanceChecker
from risk_management.tasks.generic.reserve_balance_maintainer import \
    ReserveBalanceMaintainer
from risk_management.tasks.generic.main_account_filler import MainAccountFiller
from risk_management.tasks.generic.internal_transfers_maker import \
    InternalTransfersMaker
from risk_management.models import Reserve, PortfolioLog, PNLSheet
from risk_management.tasks.generic.currency_cover import CurrencyCover
from risk_management.tasks.generic.order_cover import OrderCover

from core.models import Pair, Currency
from risk_management.models import DisabledCurrency, Cover, ReservesCover,\
    PeriodicReservesCoverSettings, Account
from nexchange.api_clients.bittrex import BittrexApiClient
from nexchange.celery import app
from decimal import Decimal
from ticker.models import Price


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=AccountBalanceChecker)
def account_balance_checker_invoke(account_id, task=None):
    task.run(account_id)


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveBalanceChecker)
def reserve_balance_checker_invoke(reserve_id, task=None):
    task.run(reserve_id)


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def currency_reserve_balance_checker_invoke(currency_code):
    reserve = Reserve.objects.get(currency__code=currency_code)
    reserve_balance_checker_invoke.apply([reserve.pk])


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def reserves_balance_checker_periodic():
    reserves = Reserve.objects.all()
    for reserve in reserves:
        reserve_balance_checker_invoke.apply_async([reserve.pk])


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
@get_task(task_cls=ReserveBalanceMaintainer)
def reserve_balance_maintainer_invoke(reserve_id, task=None):
    task.run(reserve_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def main_account_filler_invoke(account_id, amount=None, do_trade=False):
    task = MainAccountFiller()
    task.run(account_id, amount=amount, do_trade=do_trade)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def internal_transfer_invoke(currency_id, account_from_id, account_to_id,
                             amount, order_id=None, reserves_cover_id=None):
    task = InternalTransfersMaker()
    return task.run(currency_id, account_from_id, account_to_id, amount,
                    order_id=order_id, reserves_cover_id=reserves_cover_id)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def order_cover_invoke(order_id):
    task = OrderCover()
    cover, send_to_main, amount = task.run(order_id)
    if send_to_main and amount:
        account_from = cover.account
        currency = account_from.reserve.currency
        account_to = account_from.reserve.main_account
        internal_transfer_invoke.apply_async(
            args=[currency.pk, account_from.pk, account_to.pk, amount],
            kwargs={'order_id': order_id},
            countdown=settings.THIRD_PARTY_TRADE_TIME
        )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def currency_cover_invoke(currency_code, amount):
    task = CurrencyCover()
    cover = task.run(currency_code, amount)
    if cover:
        main_account_filler_invoke.apply_async(
            [cover.account.pk, cover.amount_base],
            countdown=settings.THIRD_PARTY_TRADE_TIME
        )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def log_current_assets():
    new_log = PortfolioLog()
    new_log.save()


@shared_task(time_limit=settings.REPORT_TASKS_TIME_LIMIT)
def calculate_pnls(days):
    new_sheet = PNLSheet(days=days)
    new_sheet.save()


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def calculate_pnls_1day_invoke():
    calculate_pnls.apply_async([1])


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def calculate_pnls_7days_invoke():
    calculate_pnls.apply_async([7])


@shared_task(time_limit=settings.FAST_TASKS_TIME_LIMIT)
def calculate_pnls_30days_invoke():
    calculate_pnls.apply_async([30])


def set_active_status(curr, trade_direction, active=True, param='disabled',
                      editor_param='disable_{}'):
    pairs = Pair.objects.filter(**{trade_direction: curr})
    counter_trade_direction = 'base' if trade_direction == 'quote' else 'quote'
    counter_prop = editor_param.format(counter_trade_direction)
    for pair in pairs:
        counter_curr = getattr(pair, counter_trade_direction)
        setattr(
            pair, param,
            not active or not (
                active and not DisabledCurrency.objects.filter(
                    **{'currency': counter_curr, counter_prop: True}
                ).count()
            )
        )
        pair.save(update_fields=[param])


def pair_helper(trade_direction, active=True, param='disabled',
                editor_param='disable_{}'):
    prop = editor_param.format(trade_direction)
    disabled = DisabledCurrency.objects.filter(**{prop: not active})

    for curr in disabled:
        set_active_status(curr.currency, trade_direction, active=active,
                          param=param, editor_param=editor_param)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def disable_currency_quote():
    pair_helper('quote', active=False)
    pair_helper(
        'quote', active=False, param='disable_volume',
        editor_param='disable_volume_{}'
    )
    pair_helper(
        'quote', active=False, param='disable_ticker',
        editor_param='disable_ticker_{}'
    )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def enable_currency_base():
    pair_helper('base', True)
    pair_helper(
        'base', active=True, param='disable_volume',
        editor_param='disable_volume_{}'
    )
    pair_helper(
        'base', active=True, param='disable_ticker',
        editor_param='disable_ticker_{}'
    )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def disable_currency_base():
    pair_helper('base', False)
    pair_helper(
        'base', active=False, param='disable_volume',
        editor_param='disable_volume_{}'
    )
    pair_helper(
        'base', active=False, param='disable_ticker',
        editor_param='disable_ticker_{}'
    )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def enable_currency_quote():
    pair_helper('quote', True)
    pair_helper(
        'quote', active=True, param='disable_volume',
        editor_param='disable_volume_{}'
    )
    pair_helper(
        'quote', active=True, param='disable_ticker',
        editor_param='disable_ticker_{}'
    )


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def pair_disabler_periodic():
    # do not apply async, because parallel tasks made at the same time can
    # undo work of previous task due to not refreshed DB record
    disable_currency_quote.apply()
    disable_currency_base.apply()
    enable_currency_quote.apply()
    enable_currency_base.apply()


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def execute_cover(cover_pk):
    api = BittrexApiClient()
    cover = Cover.objects.get(pk=cover_pk)
    cover.pre_execute()
    cover.execute(api)


def refill_main_account(currency_pk, account_from_pk):
    """This task sends money to main account to make balance on account_from
    and main account equal.
    """
    _currency = Currency.objects.get(pk=currency_pk)
    _reserve = _currency.reserve
    reserve_balance_checker_invoke.apply([_reserve.pk])
    _account_from = Account.objects.get(pk=account_from_pk)
    _main_account = _currency.reserve.main_account
    _main_account.refresh_from_db()
    _available_from = _account_from.available
    _available_main = _main_account.available
    _allowed_diff = _reserve.allowed_diff
    _diff = _available_from - _available_main
    _amount_to_send = _diff / Decimal('2')
    _amount_to_send_in_btc = Price.convert_amount(
        _amount_to_send, _currency, 'BTC'
    )
    if _diff > _allowed_diff and _amount_to_send_in_btc >= settings.\
            MINIMUM_BTC_AMOUNT_TO_REFILL_MAIN_ACCOUNT:
        internal_transfer_invoke(_currency, _account_from, _main_account,
                                 _amount_to_send)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def refill_main_account_invoke(currency_pk, account_from_pk):
    refill_main_account(currency_pk, account_from_pk)


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def periodic_reserve_cover_invoke():
    periodic_reserve_cover = PeriodicReservesCoverSettings.objects.filter(
        current_reserves_cover__isnull=True
    )

    for p in periodic_reserve_cover:
        rc = ReservesCover(settings=p.settings)
        rc.save()
        p.current_reserves_cover = rc
        p.save()
        if p.acceptable_rate:
            execute_reserves_cover.apply_async(
                args=[rc.pk],
                kwargs={'periodic_settings_pk': p.pk}
            )
        else:
            rc.comment = '{} bad rate'.format(rc.comment if rc.comment else '')
            rc.discard = True
            rc.save()
            p.current_reserves_cover = None
            p.save()


@app.task(bind=True)
def execute_reserves_cover(self, reserves_cover_pk, periodic_settings_pk=None):
    retry = False
    r_cover = ReservesCover.objects.get(pk=reserves_cover_pk)
    r_cover.comment = '{} exec'.format(
        r_cover.comment if r_cover.comment else ''
    )
    r_cover.save()
    if r_cover.discard:
        return
    if periodic_settings_pk:
        periodic_settings = PeriodicReservesCoverSettings.objects.get(
            pk=periodic_settings_pk
        )
        assert r_cover == periodic_settings.current_reserves_cover
        r_cover.recalculate_covers()
        r_cover.refresh_from_db()
        if not periodic_settings.acceptable_rate:
            r_cover.comment += 'bad rate '
            r_cover.comment = '{} bad rate'.format(
                r_cover.comment if r_cover.comment else ''
            )
            r_cover.discard = True
            r_cover.save()
            periodic_settings.current_reserves_cover = None
            periodic_settings.save()
            return
    first_cover = r_cover.first_cover
    txs = r_cover.transaction_set.all()
    if not first_cover.coverable and not txs:
        currency, _amount = first_cover.missing_currency_amount_to_cover
        # plus 1% to avoid failure due to not enough fee
        amount = _amount * Decimal('1.01')
        account_to = first_cover.account.get_same_api_wallet(currency=currency)
        account_from = account_to.reserve.main_account
        tx = internal_transfer_invoke(
            currency.pk, account_from.pk, account_to.pk, amount,
            reserves_cover_id=r_cover.pk
        )
        assert tx.reserves_cover == r_cover
        r_cover.comment = '{} tx_sent'.format(
            r_cover.comment if r_cover.comment else ''
        )
        r_cover.save()
    covers = r_cover.cover_set.filter(
        status=Cover.INITIAL
    ).order_by('cover_type')
    for i, cover in enumerate(covers):
        if cover.coverable:
            execute_cover.apply_async(args=[cover.pk])
        else:
            retry = True
    if retry:
        self.retry(countdown=settings.THIRD_PARTY_TRADE_TIME,
                   max_retries=settings.COVER_TASK_MAX_RETRIES)
    elif periodic_settings_pk:
        periodic_settings.current_reserves_cover = None
        periodic_settings.save()
        refill_main_account_invoke.apply_async(
            [r_cover.pair.base.pk, r_cover.cover_set.latest('id').account.pk],
            countdown=settings.THIRD_PARTY_TRADE_TIME
        )
