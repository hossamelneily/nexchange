# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-03-13 09:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_auto_20180119_1512'),
        ('verification', '0010_auto_20171201_1251'),
    ]

    operations = [
        migrations.CreateModel(
            name='TradeLimit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('limit_type', models.CharField(choices=[('W', 'WITHDRAW'), ('D', 'DEPOSIT')], max_length=1)),
                ('trade_type', models.CharField(choices=[('F', 'FIAT'), ('C', 'CRYPTO')], max_length=1)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=18)),
                ('days', models.IntegerField()),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Currency')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='VerificationTier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='tradelimit',
            name='tier',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='verification.VerificationTier'),
        ),
    ]