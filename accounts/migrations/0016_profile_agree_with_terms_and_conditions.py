# Generated by Django 2.0.7 on 2018-10-18 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_auto_20180822_1537'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='agree_with_terms_and_conditions',
            field=models.BooleanField(default=True),
        ),
    ]
