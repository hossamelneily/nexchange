# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-12-16 21:10
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referral',
            name='referee',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='referrals_set',
                to=settings.AUTH_USER_MODEL),
        ),
    ]