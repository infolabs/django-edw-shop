# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from edw_shop.conf import app_settings
from edw_shop.models.product import BaseProduct
from edw_shop.money.fields import MoneyField


@python_2_unicode_compatible
class Product(BaseProduct):
    """
    Generic Product Commodity to be used whenever the merchant does not require product specific
    attributes.
    """
    # common product fields
    product_name = models.CharField(_("Product name"), max_length=255, blank=False, null=False)
    slug = models.SlugField(_("Slug"), help_text=_("Used for URLs, auto-generated from name if blank."))
    product_code = models.CharField(_("Product code"), max_length=255, unique=True, default='')
    unit_price = MoneyField(_("Unit price"), decimal_places=3,
                            help_text=_("Net price for this product"), default=0.0)
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)


    # common fields for the catalog's list- and detail views

    # filter expression used to search for a product item using the Select2 widget
    # lookup_fields = ('product_code__startswith', 'product_name__icontains',)


    class Meta:
        app_label = app_settings.APP_LABEL
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def entity_name(self):
        return self.product_name

    def __str__(self):
        return self.product_code

    def get_price(self, request):
        return self.unit_price
