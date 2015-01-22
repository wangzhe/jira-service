from django.contrib import admin
from .models import Line
from .models import ServerInfo


# Register your models here.
admin.site.register(Line)
admin.site.register(ServerInfo)