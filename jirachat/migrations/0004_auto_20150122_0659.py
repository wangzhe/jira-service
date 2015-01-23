# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jirachat', '0003_auto_20150116_0411'),
    ]

    operations = [
        migrations.AlterField(
            model_name='serverinfo',
            name='timestamp',
            field=models.CharField(max_length=255),
        ),
    ]
