# Generated by Django 2.0.7 on 2018-08-28 12:06

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('risk_management', '0027_auto_20180827_1147'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pnl',
            name='exit_price',
            field=models.DecimalField(blank=True, decimal_places=8, default=Decimal('0'), max_digits=18, null=True),
        ),
    ]
