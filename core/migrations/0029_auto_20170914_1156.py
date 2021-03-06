# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-14 11:56
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_auto_20170903_1709'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='admin_comment',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='amount',
            field=models.DecimalField(db_index=True, decimal_places=8, default=Decimal('0'), max_digits=18),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='tx_id',
            field=models.CharField(blank=True, db_index=True, default=None, max_length=100, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='tx_id_api',
            field=models.CharField(blank=True, db_index=True, default=None, max_length=55, null=True, unique=True),
        ),
    ]
