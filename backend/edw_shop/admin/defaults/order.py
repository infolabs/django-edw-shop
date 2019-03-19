# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/27c8b8bc1db5bff958c480613dcf36f03de81d2b/shop/admin/defaults/order.py
"""
from __future__ import unicode_literals

from edw.admin.entity.forms import EntityAdminForm

from edw_shop.admin.order import BaseOrderAdmin


class OrderAdmin(BaseOrderAdmin):
    """
    Admin class to be used for Order model :class:`edw_shop.models.defaults.order`
    """
    base_form = EntityAdminForm

    def get_fields(self, request, obj=None):
        fields = list(super(OrderAdmin, self).get_fields(request, obj))
        fields.extend(['shipping_address_text', 'billing_address_text'])
        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super(OrderAdmin, self).get_readonly_fields(request, obj))
        readonly_fields.extend(['shipping_address_text', 'billing_address_text'])
        return readonly_fields

    def get_search_fields(self, request):
        search_fields = list(super(OrderAdmin, self).get_search_fields(request))
        search_fields.extend(['number', 'shipping_address_text', 'billing_address_text'])
        return search_fields
