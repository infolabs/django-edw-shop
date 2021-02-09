# -*- coding: utf-8 -*-
from rest_framework import serializers


class ProductUnitSerializer(serializers.Serializer):
    """
    A serializer to additional units.
    """
    name = serializers.CharField(required=True, max_length=50)
    value = serializers.DecimalField(max_digits=10, decimal_places=3, required=True)
    discount = serializers.DecimalField(max_digits=10, decimal_places=3, required=False)
    uuid = serializers.CharField(required=True, max_length=50)
