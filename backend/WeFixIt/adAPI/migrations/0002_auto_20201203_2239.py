# Generated by Django 3.1.3 on 2020-12-03 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adAPI', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advertisement',
            name='image',
            field=models.URLField(),
        ),
    ]
