# Generated by Django 2.0.7 on 2018-12-13 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0028_payment_limit_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentpreference',
            name='has_pending_orders',
            field=models.BooleanField(default=False),
        ),
    ]
