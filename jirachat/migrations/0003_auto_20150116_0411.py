# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jirachat', '0002_serverinfo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='serverinfo',
            name='timestamp',
            field=models.DateTimeField(verbose_name=b'timestamp'),
        ),
    ]
