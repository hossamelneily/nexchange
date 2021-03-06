# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-07-04 16:31
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ico', '0005_auto_20180704_1512'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='related_turnover',
            field=models.DecimalField(blank=True, decimal_places=8, default=Decimal('0'), help_text='Turnover of all related orders. Must be equal or more than address_turnover. Converted to ETH.', max_digits=18, null=True),
        ),
    ]
