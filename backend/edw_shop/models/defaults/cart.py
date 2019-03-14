# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/7d827ac23bb81b09d64234c0f832492967f9d5bd/shop/models/defaults/cart.py
"""
from __future__ import unicode_literals

from django.db.models import SET_DEFAULT

from edw import deferred
from edw_shop.models.address import BaseShippingAddress, BaseBillingAddress
from edw_shop.models.cart import BaseCart


class Cart(BaseCart):
    """
    Default materialized model for BaseCart containing common fields
    """
    shipping_address = deferred.ForeignKey(
        BaseShippingAddress,
        null=True,
        default=None,
        related_name='+',
        on_delete=SET_DEFAULT,
    )

    billing_address = deferred.ForeignKey(
        BaseBillingAddress,
        null=True,
        default=None,
        related_name='+',
        on_delete=SET_DEFAULT,
    )
