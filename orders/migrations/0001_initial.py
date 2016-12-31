# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-12-15 22:14
from __future__ import unicode_literals

import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.BooleanField(default=False)),
                ('disabled', models.BooleanField(default=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('order_type', models.IntegerField(choices=[(0, 'SELL'), (1, 'BUY')], default=1)),
                ('amount_cash', models.DecimalField(decimal_places=2, max_digits=12)),
                ('amount_btc', models.DecimalField(decimal_places=8, max_digits=18)),
                ('payment_window', models.IntegerField(default=60)),
                ('is_paid', models.BooleanField(default=False)),
                ('is_released', models.BooleanField(default=False)),
                ('is_completed', models.BooleanField(default=False)),
                ('is_failed', models.BooleanField(default=False)),
                ('unique_reference', models.CharField(max_length=5, unique=True)),
                ('admin_comment', models.CharField(max_length=200)),
            ],
            options={
                'ordering': ['-created_on'],
            },
            managers=[
                ('active_objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
