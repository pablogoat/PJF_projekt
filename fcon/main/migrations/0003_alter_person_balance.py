# Generated by Django 4.0.5 on 2022-07-23 11:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_debetor_share'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='balance',
            field=models.FloatField(default=0),
        ),
    ]
