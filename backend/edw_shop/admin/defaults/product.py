# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.contrib import admin

from edw.admin.entity import (
    EntityCharacteristicOrMarkInline,
    EntityRelationInline,
    EntityRelatedDataMartInline,
    EntityChildModelAdmin,
)
from edw.admin.entity.entity_image import EntityImageInline
from edw.admin.entity.entity_file import EntityFileInline

from edw_shop.admin.defaults.forms import EntityAdminForm
from edw_shop.models.defaults.product import ProductUnit

class ProductUnitAdminInline(admin.TabularInline):
    model = ProductUnit
    extra = 0

class ProductAdmin(EntityChildModelAdmin):

    base_form = EntityAdminForm

    inlines = [
        ProductUnitAdminInline,
        EntityCharacteristicOrMarkInline,
        EntityRelationInline,
        EntityRelatedDataMartInline,
        EntityImageInline,
        EntityFileInline
    ]

    prepopulated_fields = {'slug': ['product_name']}

    list_display = ['product_name', 'sid', 'unit_price', 'created_at', 'updated_at', 'active']

    base_fieldsets = (
        (_("Main params"), {
            'fields': ('product_name', 'slug', 'product_code', 'unit_price', 'active', 'created_at',
                       'terms', 'description'),
        }),
    )
    search_fields = ['product_name', 'sid',]
    save_as = True

    readonly_fields = []

    def view_on_site(self, obj):
        return obj.get_detail_url()
