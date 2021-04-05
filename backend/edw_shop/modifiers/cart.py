# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/c59a68fb8337409b4fe35c261e95366cd456ff0a/shop/modifiers/defaults.py
"""
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from edw_shop.serializers.cart import ExtraCartRow
from .base import BaseCartModifier
import decimal

class QuantityCartModifier(BaseCartModifier):
    """
    This modifier is required for almost every shopping cart. It handles the most basic
    calculations, ie. multiplying the items unit prices with the chosen quantity.
    Since this modifier sets the cart items line total, it must be listed as the first
    entry in `SHOP_CART_MODIFIERS`.
    """
    def __init__(self, identifier=None):
        """
        Initialize the modifier with a named identifier. Defaults to its classname.
        """
        self.label = _("Discount for quantity")
        return super(QuantityCartModifier, self).__init__(identifier)

    def process_cart_item(self, cart_item, request):

        cart_item.unit_price = decimal.Decimal(cart_item.product.get_price(request))
        cart_item.line_total = decimal.Decimal(cart_item.unit_price * cart_item.quantity)
        return super(QuantityCartModifier, self).process_cart_item(cart_item, request)

    def add_extra_cart_item_row(self, cart_item, request):
        product_unit = cart_item.product.get_unit_by_quantity(cart_item.quantity)
        if product_unit:
            amount = decimal.Decimal(cart_item.quantity * product_unit["price"]) - cart_item.line_total
            cart_item.line_total = cart_item.line_total + amount
            instance = {
                'label': "{}: {:.2f}".format(self.label, amount),
                'amount': amount,
            }
            cart_item.extra_rows[self.identifier] = ExtraCartRow(instance)

        return super(QuantityCartModifier, self).add_extra_cart_item_row(cart_item, request)


    def process_cart(self, cart, request):
        cart.total = cart.subtotal
        return super(QuantityCartModifier, self).process_cart(cart, request)

