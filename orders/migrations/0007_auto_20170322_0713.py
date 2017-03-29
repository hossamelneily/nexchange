# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-22 07:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_auto_20170316_0737'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='exchange',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_type',
            field=models.IntegerField(choices=[(0, 'SELL'), (1, 'BUY')], default=1, help_text='BUY - Customer is giving fiat, and getting crypto money.<br/>SELL - Customer is giving crypto and getting fiat money<br/>EXCHANGE - Customer is exchanging different kinds of crypto currencies<br/>'),
        ),
    ]