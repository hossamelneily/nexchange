# Generated by Django 2.0.7 on 2018-08-22 15:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0002_suspicioustransactions_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suspicioustransactions',
            name='currency',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='core.Currency'),
        ),
    ]
