# Generated by Django 2.0.7 on 2018-08-24 09:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_auto_20180823_1306'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurrencyAlgorithm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('modified_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(default='empty', max_length=15)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='currency',
            name='algo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='core.CurrencyAlgorithm'),
        ),
        migrations.AlterField(
            model_name='transactionprice',
            name='algo',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='core.CurrencyAlgorithm'),
        ),
    ]
