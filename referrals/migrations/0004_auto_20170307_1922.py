# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-07 19:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0003_referralcode_link'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='percent_first_degree',
            field=models.DecimalField(
                decimal_places=8,
                default=0,
                max_digits=18),
        ),
    ]
