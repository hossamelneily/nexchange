from orders.models import Order
from django.core.management import BaseCommand


class Command(BaseCommand):
    # Show this when the user types help
    help = "Migrate order statuses to incremental statuses"

    # A command must define handle()
    def handle(self, *args, **options):
        orders_initial = Order.objects.filter(status=1)
        orders_paid_unconfirmed = Order.objects.filter(status=-1)
        orders_paid = Order.objects.filter(status=2)
        orders_released = Order.objects.filter(status=3)
        orders_completed = Order.objects.filter(status=4)
        orders_pre_release = Order.objects.filter(status=-2)
        for order in orders_initial:
            order.status = 11
            order.save()
        for order in orders_paid_unconfirmed:
            order.status = 12
            order.save()
        for order in orders_paid:
            order.status = 13
            order.save()
        for order in orders_pre_release:
            order.status = 14
            order.save()
        for order in orders_released:
            order.status = 15
            order.save()
        for order in orders_completed:
            order.status = 16
            order.save()

        self.stdout.write("Order statuses Migrated!")
