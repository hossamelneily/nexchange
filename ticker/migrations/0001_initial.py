# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-12-15 22:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Price',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('type', models.CharField(choices=[('B', 'BUY'), ('S', 'SELL')], max_length=1)),
                ('price_rub', models.DecimalField(decimal_places=2, max_digits=12)),
                ('price_usd', models.DecimalField(decimal_places=2, max_digits=12)),
                ('price_eur', models.DecimalField(decimal_places=2, max_digits=12)),
                ('rate_usd', models.DecimalField(decimal_places=2, max_digits=12)),
                ('rate_eur', models.DecimalField(decimal_places=2, max_digits=12)),
                ('better_adds_count', models.IntegerField(default=0)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
