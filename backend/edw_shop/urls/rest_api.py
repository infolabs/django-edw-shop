# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url, include
from rest_framework import routers

from edw_shop.views.cart import CartViewSet


router = routers.DefaultRouter()  # TODO: try with trailing_slash=False
router.register(r'cart', CartViewSet, base_name='cart')

urlpatterns = [
    url(r'^', include(router.urls)),
]
