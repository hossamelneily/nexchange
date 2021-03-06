# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-02-28 01:03
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('risk_management', '0010_auto_20180216_1224'),
    ]

    operations = [
        migrations.AddField(
            model_name='pnl',
            name='base_position',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='pnl',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='pnl_eth',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='pnl_eur',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='pnl_realized',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='pnl_unrealized',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='pnl_usd',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='position',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='pnl',
            name='realized_volume',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
    ]
