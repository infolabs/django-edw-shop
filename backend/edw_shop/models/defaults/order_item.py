# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/41bdcdfb3a6af80839b6ce41f0e0ecce9582e039/shop/models/defaults/order_item.py
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from shop.models import order


class OrderItem(order.BaseOrderItem):
    """Default materialized model for OrderItem"""
    quantity = models.IntegerField(_("Ordered quantity"))
