# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-04-16 11:27
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('risk_management', '0010_auto_20180216_1224'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserve',
            name='maximal_limit_balance',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
    ]