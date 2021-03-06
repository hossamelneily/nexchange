# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-02-14 10:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_auto_20180119_1512'),
        ('orders', '0023_order_slippage'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='refund_address',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_set_refund', to='core.Address'),
        ),
    ]
