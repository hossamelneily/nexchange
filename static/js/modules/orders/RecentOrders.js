import moment from 'moment';
import Extractor from '../helpers/Extractor.js';

const ORDER_TYPE = {
    0: 'SELL',
    1: 'BUY'
};

class RecentOrders {
    constructor() {
        this.recentOrdersEndpoint = '/en/api/v1/orders/?page=1';
        this.updateInterval = 10000;
        this.recentOrdersLength = parseInt($('#recent-orders').data('recent-orders-length'));
        this.updateOrders();
    }

    updateOrders() {
        let request = $.get(this.recentOrdersEndpoint);

        request.success(orders => {
            setTimeout(this.updateOrders.bind(this), this.updateInterval);
            if (!orders.results.length) return;

            let updatedOrders = ``;
            for (let order of orders.results.slice(0, this.recentOrdersLength)) {
                updatedOrders += this.constructOrderRow(order);
            }
            $('.recent-order').remove();
            $('#recent-orders .table-order').after(updatedOrders);
        });
      
        request.error((jqXHR, textStatus, errorThrown) => {
            setTimeout(this.updateOrders.bind(this), this.updateInterval);

            if (textStatus == 'timeout') {
                console.log('The server is not responding');
            }

            if (textStatus == 'error') {
                console.log(errorThrown);
            }
        });
    }

    constructOrderRow(order) {
        let currencies = Extractor.getCurrenciesFromPair(order.pair_name),
            created_on = new moment(order.created_on).fromNow(),
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
            <td><i class="fa ${icon}" aria-hidden="true"></i> ${created_on}</td>
            <td>${parseFloat(sendingAmount).toFixed(2)} ${sendingCurrency}</td>
            <td>${parseFloat(receivingAmount).toFixed(2)} ${receivingCurrency}</td>
            <td>${rate} ${receivingCurrency}</td>
        </tr>`;
    }
}

export default new RecentOrders();