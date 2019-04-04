# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from edw.models.term import TermModel

from edw_shop.conf import app_settings
from edw_shop.models.product import BaseProduct
from edw_shop.money.fields import MoneyField

from edw_fluent.models.page_layout import (
    get_views_layouts,
    get_layout_slug_by_model_name,
    get_or_create_view_layouts_root
)

_publication_root_terms_system_flags_restriction = (
    TermModel.system_flags.delete_restriction
    | TermModel.system_flags.change_parent_restriction
    | TermModel.system_flags.change_slug_restriction
)


@python_2_unicode_compatible
class Product(BaseProduct):
    """
    Generic Product Commodity to be used whenever the merchant does not require product specific
    attributes.
    """
    VIEW_COMPONENT_TILE = 'tile'
    VIEW_COMPONENT_LIST = 'list'

    VIEW_COMPONENTS = (
        (VIEW_COMPONENT_TILE, _('Tile')),
        (VIEW_COMPONENT_LIST, _('List')),
    )

    LAYOUT_TERM_SLUG = get_layout_slug_by_model_name('publication')

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

    class RESTMeta:
        lookup_fields = ('id', 'slug')
        include = {
            'detail_url': ('rest_framework.serializers.CharField', {
                'source': 'get_detail_url',
                'read_only': True
            }),
        }

    @property
    def entity_name(self):
        return self.product_name

    def __str__(self):
        return self.product_name

    def get_detail_url(self, data_mart=None):
        if data_mart is None:
            data_mart = self.data_mart
        if data_mart:
            page = data_mart.get_cached_detail_page()
            return reverse('product_detail', args=[page.url.strip('/'), self.pk] if page is not None else [self.pk])
        else:
            return reverse('product_detail', args=[self.pk])

    def get_summary_extra(self, context):
        data_mart = context['data_mart']
        extra = {
            'url': self.get_detail_url(data_mart)
        }
        return extra

    def get_price(self, request):
        return self.unit_price

    @classmethod
    def validate_term_model(cls):
        view_root = get_or_create_view_layouts_root()
        try:  # product root
            TermModel.objects.get(slug=cls.LAYOUT_TERM_SLUG, parent=view_root)
        except TermModel.DoesNotExist:
            publication_root = TermModel(
                slug=cls.LAYOUT_TERM_SLUG,
                parent=view_root,
                name=_('Product'),
                semantic_rule=TermModel.XOR_RULE,
                system_flags=_publication_root_terms_system_flags_restriction
            )
            publication_root.save()

        super(Product, cls).validate_term_model()

    def need_terms_validation_after_save(self, origin, **kwargs):
        do_validate_layout = kwargs["context"]["validate_view_layout"] = True

        return super(Product, self).need_terms_validation_after_save(
            origin, **kwargs) or do_validate_layout

    def validate_terms(self, origin, **kwargs):
        context = kwargs["context"]

        force_validate_terms = context.get("force_validate_terms", False)

        if force_validate_terms or context.get("validate_view_layout", False):
            views_layouts = get_views_layouts()
            to_remove = [v for k, v in views_layouts.items() if k != Product.LAYOUT_TERM_SLUG]
            self.terms.remove(*to_remove)
            to_add = views_layouts.get(Product.LAYOUT_TERM_SLUG, None)
            if to_add is not None:
                self.terms.add(to_add)

        super(Product, self).validate_terms(origin, **kwargs)
