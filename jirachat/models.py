from django.db import models


# Create your models here.
class Line(models.Model):
    text = models.CharField(max_length=255)


class ServerInfo(models.Model):
    signature = models.CharField(max_length=255)
    timestamp = models.DateTimeField('timestamp')
    nonce = models.CharField(max_length=255)
    echostr = models.CharField(max_length=255)
