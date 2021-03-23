# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, url

from . import rest_api


urlpatterns = [
    url(r'^api/', include(rest_api)),
]
