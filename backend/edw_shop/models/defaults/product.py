# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from edw.models.term import TermModel

from edw_shop.conf import app_settings
from edw_shop.models.product import BaseProduct
from edw_shop.money.fields import MoneyField

from edw_shop.rest.validators.product import ProductValidator

from edw_fluent.models.page_layout import (
    get_views_layouts,
    get_layout_slug_by_model_name,
    get_or_create_view_layouts_root
)

from sid.models.entity import EntityImage, EntityFile

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

    sid = models.CharField(verbose_name=_('SID'), max_length=255, unique=True, null=True, blank=True,
                           help_text=_("Secondary ID needed for purposes of external exchange system."))

    sku = models.CharField(verbose_name=_('SKU'), max_length=255, null=True, blank=True, default='',
                           help_text=_("Show in product detail description"))

    product_code = models.CharField(_("Product code"), max_length=255, default='', blank=True, null=True)

    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)

    unit = models.CharField(verbose_name=_('measurment unit'), max_length=50, null=True, blank=True, default='',
                            help_text=_("Basic measurement unit of product"))

    unit_price = MoneyField(_("Unit price"), decimal_places=3,
                            help_text=_("Net price for this product"), default=0.0)

    step = models.DecimalField(verbose_name=_('addition step'), default=1, max_digits=10, decimal_places=3,
                               help_text=_(
                                   "Step for sale product. For example: You set price is per linear meter, but the product is only sold by the piece, the length of one piece 1.49 meters. Set step as 1.49"))

    is_display_price_per_step = models.BooleanField(default=False,
                                                    verbose_name=_('Display price per step instead one unit price'))

    in_stock = models.IntegerField(verbose_name=_('quantity in stock'), null=True, blank=True, help_text=_(
        """"" - out of stock; "0" - sold out; "N" - N quantity in stock"""))

    estimated_delivery = models.CharField(max_length=255, verbose_name=_('estimated delivery'), null=True, blank=True,
                                          help_text=_("""If not empty then show this instead "in stock" or "out of stock" """))

    # common fields for the catalog's list- and detail views

    # filter expression used to search for a product item using the Select2 widget
    # lookup_fields = ('product_code__startswith', 'product_name__icontains',)

    class Meta:
        app_label = app_settings.APP_LABEL
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    class RESTMeta:
        lookup_fields = ('id', 'slug')

        validators = [ProductValidator()]


        include = {
            'detail_url': ('rest_framework.serializers.CharField', {
                'source': 'get_detail_url',
                'read_only': True
            }),
            'gallery': ('edw.rest.serializers.related.entity_image.EntityImageSerializer', {
                'read_only': True,
                'many': True
            }),
            'thumbnail': ('edw.rest.serializers.related.entity_image.EntityImageSerializer', {
                'read_only': True,
                'many': True
            }),
            'attachments': ('edw.rest.serializers.related.entity_file.EntityFileSerializer', {
                'read_only': True,
                'many': True
            }),
            'product_code': ('rest_framework.serializers.CharField', {'required': False})
        }

        @staticmethod
        def _update_entity(self, instance, validated_data):

            # если есть текстовый контент заменяем все содержание публикации
            html_content = validated_data.pop('html_content', None)


        def create(self, validated_data):

            origin_validated_data = validated_data.copy()

            for key in ('transition', 'html_content'):
                validated_data.pop(key, None)

            instance = super(self.__class__, self).create(validated_data)

            #self.Meta.model.RESTMeta._get_or_create_placeholder(self, instance)
            self.Meta.model.RESTMeta._update_entity(self, instance, origin_validated_data)

            return instance

        def update(self, instance, validated_data):

            self.Meta.model.RESTMeta._update_entity(self, instance, validated_data)
            return super(self.__class__, self).update(instance, validated_data)


    @property
    def entity_name(self):
        return self.product_name

    def __str__(self):
        return self.product_name

    #product properties
    @property
    def get_sid(self):
        return self.sid if self.sid else ""


    @property
    def get_sku(self):
        return self.sku if self.sku else ""

    @property
    def get_product_code(self):
        return self.product_code if self.product_code else ""

    @property
    def get_unit(self):
        return self.unit if self.unit else ""

    @property
    def get_step(self):
        return self.step

    @property
    def get_unit_price(self):
        return self.unit_price

    @property
    def get_is_display_price_per_step(self):
        return self.is_display_price_per_step

    @property
    def get_in_stock(self):

        return self.in_stock if self.in_stock else 0

    @property
    def get_estimated_delivery(self):
        return self.estimated_delivery if self.estimated_delivery else ""

    def get_price(self, request):
        return self.unit_price


    def get_detail_url(self, data_mart=None):
        if data_mart is None:
            data_mart = self.data_mart
        if data_mart:
            page = data_mart.get_cached_detail_page()
            return reverse('product_detail', args=[page.url.strip('/'), self.pk] if page is not None else [self.pk])
        else:
            return reverse('product_detail', args=[self.pk])

    @cached_property
    def breadcrumbs(self):
        data_mart = self.data_mart

        if data_mart:
            page = data_mart.get_cached_detail_page()
            if page:
                return page.breadcrumb

        return None

    def get_summary_extra(self, context):
        data_mart = context['data_mart']
        extra = {
            'url': self.get_detail_url(data_mart),
            'slug': self.slug,
            'sid':  self.get_sid,
            'sku': self.get_sku,
            'product_code': self.get_product_code,
            'unit': self.get_unit,
            'step': self.get_step,
            'unit_price': self.get_unit_price,
            'is_display_price_per_step': self.get_is_display_price_per_step,
            'in_stock': self.get_in_stock,
            'estimated_delivery': self.get_estimated_delivery
        }

        return extra

    def get_price(self, request):
        return self.unit_price

    @cached_property
    def gallery(self):
        return list(self.get_gallery())

    def get_gallery(self):
        return EntityImage.objects.filter(entity=self, key=None).select_related('image').order_by('order')

    @cached_property
    def thumbnail(self):
        return list(self.get_thumbnail())

    def get_thumbnail(self):
        return EntityImage.objects.filter(entity=self, key=EntityImage.THUMBNAIL_KEY).order_by('order')

    @cached_property
    def attachments(self):
        return list(self.get_attachments())

    def get_attachments(self):
        return EntityFile.objects.filter(entity=self, key=None).order_by('order')

    @cached_property
    def thumbnails(self):
        thumbnails = [x.image for x in
                      EntityImage.objects.filter(entity=self, key=EntityImage.THUMBNAIL_KEY).order_by('order')]
        if thumbnails:
            return thumbnails
        else:
            thumbnails = [x.image for x in self.gallery]
            if thumbnails:
                return thumbnails[:1]
            else:
                return self.ordered_images[:1]


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
