# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/fd9d6408c74bb32ad9efaa8b3b9752266702f59f/shop/models/defaults/cart_item.py
"""
from __future__ import unicode_literals

from django.core.validators import MinValueValidator
from django.db.models import IntegerField
from edw_shop.models import cart


class CartItem(cart.BaseCartItem):
    """Default materialized model for CartItem"""
    quantity = IntegerField(validators=[MinValueValidator(0)])
