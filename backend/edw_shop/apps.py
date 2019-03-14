# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/3a069d764a7b72ef119828220869dcfbbfc1b9c5/shop/apps.py
"""
from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ShopConfig(AppConfig):
    name = 'edw_shop'
    verbose_name = _("Shop")

    def ready(self):
        #from django_fsm.signals import post_transition
        from edw_shop.models.fields import JSONField
        from rest_framework.serializers import ModelSerializer
        from edw.deferred import ForeignKeyBuilder
        from edw_shop.rest.fields import JSONSerializerField
        #from edw_shop.models.notification import order_event_notification

        #post_transition.connect(order_event_notification)

        # add JSONField to the map of customized serializers
        ModelSerializer.serializer_field_mapping[JSONField] = JSONSerializerField

        # perform some sanity checks
        ForeignKeyBuilder.check_for_pending_mappings()
