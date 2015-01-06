from django.conf.urls import patterns, include, url
from django.contrib import admin
from jirachat import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^blog/', include('blog.urls')),
    # url(r'^jirachat/', include(jirachat.site.urls)),

    url(r'^$', 'jirachat.views.home', name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^wechat/', 'jirachat.views.wechat', name='wechat'),
)
