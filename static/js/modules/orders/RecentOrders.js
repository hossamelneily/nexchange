import moment from 'moment';

const ORDER_TYPE = {
    0: 'SELL',
    1: 'BUY'
};

export default class RecentOrders {
    constructor() {
        this.recentOrdersEndpoint = '/en/api/v1/orders/';
        this.updateInterval = 10000;
        this.recentOrdersLength = parseInt($('#recent-orders').data('recent-orders-length'));
        this.updateOrders();
    }

    updateOrders() {
        $.get(this.recentOrdersEndpoint, orders => {
            setTimeout(this.updateOrders.bind(this), this.updateInterval);
            if (!orders.length) return;

            let updatedOrders = ``;
            for (let order of orders.slice(0, this.recentOrdersLength)) {
                updatedOrders += this.constructOrderRow(order);
            }
            $('.recent-order').remove();
            $('#recent-orders .table-order').after(updatedOrders);
        });
    }

    extractCurrencies(pair) {
        let first = pair.slice(0,3);
        let second = pair.slice(3,6);
        return [first, second];
    }

    constructOrderRow(order) {
        let currencies = this.extractCurrencies(order.pair_name),
            created_on = new moment(order.created_on).format('MMM Do, h:mm a'),
            sendingAmount,
            receivingAmount,
            sendingCurrency,
            receivingCurrency;

        if (ORDER_TYPE[order.order_type] == 'BUY') {
            sendingAmount = order.amount_quote;
            receivingAmount = order.amount_base;
            sendingCurrency = currencies[1];
            receivingCurrency = currencies[0];
        } else if (ORDER_TYPE[order.order_type] == 'SELL') {
            sendingAmount = order.amount_base;
            receivingAmount = order.amount_quote;
            sendingCurrency = currencies[0];
            receivingCurrency = currencies[1];
        }

        let rate = parseFloat(receivingAmount / sendingAmount).toFixed(5);
        let icon = order.from_default_rule ? 'fa-cogs' : 'fa-user';

        return `<tr class="recent-order" data-ref="${order.unique_reference}">
            <td>${created_on}</td>
            <td class="text-center"><i class="fa ${icon}" aria-hidden="true"></i></td>
            <td>${parseFloat(sendingAmount).toFixed(2)} ${sendingCurrency}</td>
            <td>${parseFloat(receivingAmount).toFixed(2)} ${receivingCurrency}</td>
            <td>${rate}</td>
        </tr>`;
    }
}