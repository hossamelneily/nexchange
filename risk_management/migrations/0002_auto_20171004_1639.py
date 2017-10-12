# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-10-04 16:39
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('risk_management', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserve',
            name='expected_balance',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AddField(
            model_name='reserve',
            name='is_limit_reserve',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='reserve',
            name='margin_balance',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
    ]
