# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/8c12f30d65fed68902dcca802b13d3418a54067a/shop/shipping/base.py
"""
from __future__ import unicode_literals


class ShippingProvider(object):
    """
    Base class for all Shipping Providers.
    """
    @property
    def namespace(self):
        """
        Use a unique namespace for this shipping provider. It is used to keep state over how each
        item was shipped to the customer.
        """
        msg = "The attribute `namespace` must be implemented by the class `{}`"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    def get_urls(self):
        """
        Return a list of URL patterns for external communication with the shipping service provider.
        """
        return []
