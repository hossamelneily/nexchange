# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-05-29 14:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0022_auto_20180331_1336'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='type',
            field=models.CharField(choices=[('W', 'WITHDRAW'), ('D', 'DEPOSIT'), ('R', 'REFUND'), ('I', 'INTERNAL')], max_length=1, null=True),
        ),
    ]