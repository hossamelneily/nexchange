# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-04-20 09:32
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('risk_management', '0013_merge_20180418_1312'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserve',
            name='minimum_main_account_level',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
    ]
