# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/2c5435ce70567bebdb80030100a791b39720b361/shop/serializers/bases.py
"""
from __future__ import unicode_literals
from rest_framework import serializers

from edw.models.customer import CustomerModel
from edw_shop.models.order import OrderItemModel
from edw_shop.rest.money import MoneyField


class BaseCustomerSerializer(serializers.ModelSerializer):
    number = serializers.CharField(source='get_number')

    class Meta:
        model = CustomerModel
        fields = ['number', 'first_name', 'last_name', 'email']


class BaseOrderItemSerializer(serializers.ModelSerializer):
    line_total = MoneyField()
    unit_price = MoneyField()
    product_code = serializers.CharField()

    class Meta:
        model = OrderItemModel
