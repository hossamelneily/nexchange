# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-01-30 15:40
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('risk_management', '0007_cover_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortfolioLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ReserveLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('available', models.DecimalField(blank=True, decimal_places=8, default=Decimal('0'), max_digits=18)),
                ('rate_btc', models.DecimalField(blank=True, decimal_places=8, default=Decimal('0'), max_digits=18)),
                ('rate_usd', models.DecimalField(blank=True, decimal_places=8, default=Decimal('0'), max_digits=18)),
                ('rate_eur', models.DecimalField(blank=True, decimal_places=8, default=Decimal('0'), max_digits=18)),
                ('rate_eth', models.DecimalField(blank=True, decimal_places=8, default=Decimal('0'), max_digits=18)),
                ('portfolio_log', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='risk_management.PortfolioLog')),
                ('reserve', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='risk_management.Reserve')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
