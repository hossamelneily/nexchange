# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-17 10:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0011_auto_20170112_1117'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cmspage',
            name='name',
            field=models.CharField(choices=[('faq', 'faq'), ('fees', 'fees'), ('support', 'support'), ('about_us', 'about_us'), ('careers', 'careers'), ('press', 'press'), ('conference', 'conference'), ('legal_privacy', 'legal_privacy'), ('security', 'security')], default=None, max_length=50),
        ),
        migrations.AlterField(
            model_name='ogresource',
            name='name',
            field=models.CharField(choices=[('faq', 'faq'), ('fees', 'fees'), ('support', 'support'), ('about_us', 'about_us'), ('careers', 'careers'), ('press', 'press'), ('conference', 'conference'), ('legal_privacy', 'legal_privacy'), ('security', 'security')], default=None, max_length=50),
        ),
    ]
