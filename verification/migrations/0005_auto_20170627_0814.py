# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-27 08:14
from __future__ import unicode_literals

from django.db import migrations, models
import verification.models
import verification.validators


class Migration(migrations.Migration):

    dependencies = [
        ('verification', '0004_auto_20170626_2031'),
    ]

    operations = [
        migrations.AlterField(
            model_name='verification',
            name='identity_document',
            field=models.FileField(upload_to=verification.models.Verification.identity_file_name, validators=[verification.validators.validate_image_extension]),
        ),
        migrations.AlterField(
            model_name='verification',
            name='utility_document',
            field=models.FileField(upload_to=verification.models.Verification._utility_file_name, validators=[verification.validators.validate_image_extension]),
        ),
    ]