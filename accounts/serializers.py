from orders.serizalizers import MetaFlatOrder, OrderSerializer


class UserOrderSerializer(OrderSerializer):
    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields +\
                 ('status', 'payment_window',
                  'payment_deadline', 'pair')
