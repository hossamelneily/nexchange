# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-10-04 13:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0067_seofooter_written_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='seofooter', name='type', field=models.CharField(
                choices=[
                    ('w', 'WITHDRAW'), ('d', 'DEPOSIT')], default=None, max_length=50), ), ]
