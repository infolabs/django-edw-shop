# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.utils.encoding import force_text

from edw.models.mixins.entity import get_or_create_model_class_wrapper_term, ENTITY_CLASS_WRAPPER_TERM_SLUG_PATTERN
from edw.models.term import TermModel
from edw import deferred

from edw_shop.conf import app_settings
from edw_shop.models.product import BaseProduct
from edw_shop.models.utils import get_or_create_term_wrapper, _default_system_flags_restriction
from edw_shop.money.fields import MoneyField

from edw_shop.rest.validators.product import ProductValidator
from edw_shop.rest.serializers.product import ProductUnitSerializer

from edw_fluent.models.page_layout import (
    get_views_layouts,
    get_layout_slug_by_model_name,
    get_or_create_view_layouts_root
)
from decimal import Decimal
from sid.models.entity import EntityImage, EntityFile

_default_root_terms_system_flags_restriction = (
    TermModel.system_flags.delete_restriction
    | TermModel.system_flags.change_parent_restriction
    | TermModel.system_flags.change_slug_restriction
)

_full_root_terms_system_flags_restriction = (
    TermModel.system_flags.delete_restriction
    | TermModel.system_flags.change_parent_restriction
    | TermModel.system_flags.change_slug_restriction
    | TermModel.system_flags.change_semantic_rule_restriction
    | TermModel.system_flags.has_child_restriction
    | TermModel.system_flags.external_tagging_restriction
)

@python_2_unicode_compatible
class Product(BaseProduct):
    """
    Generic Product Commodity to be used whenever the merchant does not require product specific
    attributes.
    """
    VIEW_COMPONENT_TILE = 'product_tile'
    VIEW_COMPONENT_LIST = 'product_list'

    VIEW_COMPONENTS = (
        (VIEW_COMPONENT_TILE, _('Tile')),
        (VIEW_COMPONENT_LIST, _('List')),
    )

    ORDER_BY_IN_STOCK = '-product__in_stock'
    ORDER_BY_NAME_DESC = '-product__product_name'
    ORDER_BY_NAME_ASC = 'product__product_name'

    ORDERING_MODES = (
        (ORDER_BY_IN_STOCK, _('In stock first')),
        (ORDER_BY_NAME_ASC, _('By name: Alphabetical')),
        (ORDER_BY_NAME_DESC, _('By name: Alphabetical desc')),
        (BaseProduct.ORDER_BY_CREATED_AT_DESC, _('Created at: new first')),
    )

    LAYOUT_TERM_SLUG = get_layout_slug_by_model_name('product')

    IN_STOCK_ROOT_TERM = ('stock_choice', _('stock'))
    IN_STOCK_CHOICES_TERMS = (
        ('in_stock', _('in stock')),
        ('out_of_stock', _('out of stock'))
    )

    PRODUCER_TERM_SLUG = 'product_producer'
    CATEGORY_TERM_PATTERN = 'commercml_category'

    # common product fields
    product_name = models.CharField(_("Product name"), max_length=255, blank=False, null=False)
    slug = models.SlugField(_("Slug"), help_text=_("Used for URLs, auto-generated from name if blank."))

    sid = models.CharField(verbose_name=_('Secondary ID'), max_length=255, unique=True, null=True, blank=True,
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

    def has_additional_units(self):
        return True if self.units.all().count() > 0 else False
    has_additional_units.short_description = _('has units')

    class RESTMeta:
        lookup_fields = ('id', 'uuid', 'slug',)

        validators = [ProductValidator()]

        #exclude = ['sid']

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
            'product_code': ('rest_framework.serializers.CharField', {'required': False}),

            'uuid': ('rest_framework.serializers.CharField', {
                'required': False,
            }),
            'slug': ('rest_framework.serializers.CharField', {'required': False}), # 'write_only': True})
            'extra_units': ('rest_framework.serializers.ListField', {
                'child': ProductUnitSerializer(),
                'required': False,
                'write_only': True
            }),
            'price': ('rest_framework.serializers.DecimalField', {
                'max_digits':10,
                'decimal_places': 3,
                'source': 'get_unit_price',
                'read_only': True
            }),
            'units':('rest_framework.serializers.ListField', {
                'source': 'get_units',
                'read_only': True
            }),
            'default_data_mart': ('edw.rest.serializers.entity.RelatedDataMartSerializer', {
                'source': 'data_mart',
                'read_only': True
            }),
            'producer' : ('edw_shop.rest.serializers.product.ProductProducerSerializer', {
                'required': False,
                'write_only': True
            })
        }

        @staticmethod
        def _update_entity(self, instance, is_created, validated_data):

            # если есть текстовый контент заменяем все содержание публикации
            html_content = validated_data.pop('html_content', None)
            # экстра единицы измерения
            units = validated_data.pop("extra_units", None)
            if units is not None:
                for unit in units:
                    instance.units.update_or_create(uuid=unit.get("uuid"),
                                                    defaults={"value": unit.get("value", 1.0),
                                                              "name": unit.get("name"),
                                                              "discount": unit.get("discount", 1.0)})
            # создаем копии производителя категориям
            producer = validated_data.pop("producer", None)
            if producer is not None:
                producer_name = producer['name']
                producer_guid = producer['guid']
                categories = producer['categories']
                root_producer_term_slug = producer['root_producer']

                if categories:
                    for category in categories:
                        category_term = TermModel.objects.active().get(slug=category)
                        if category_term:
                            root_category = get_or_create_term_wrapper(category_term)

                            # Получаем термин папки производитель
                            producer_root_tag, created = root_category.get_children().get_or_create(
                                slug=instance.PRODUCER_TERM_SLUG,
                                defaults={
                                    "parent_id": root_category.id,
                                    "name": u'Производитель',#_("Producer"),
                                    "semantic_rule": TermModel.OR_RULE,
                                    "attributes": TermModel.attributes.is_characteristic,
                                    "specification_mode": TermModel.SPECIFICATION_MODES[1][0],
                                    "system_flags": _default_system_flags_restriction

                                })

                            # Получаем термин производителя
                            product_producer_term, created = producer_root_tag.get_children().get_or_create(
                                slug=producer_guid,
                                defaults={
                                    "parent_id": producer_root_tag.id,
                                    "name": producer_name,
                                    "semantic_rule": TermModel.OR_RULE,
                                    "system_flags": _default_system_flags_restriction
                                })

                            if not created and product_producer_term.name != producer_name:
                                product_producer_term.name = producer_name
                                product_producer_term.save()

                            # устанавливаем в товар
                            instance.terms.add(product_producer_term)
                            # усли update добавляем в active_terms_ids
                            if validated_data.get('active_terms_ids', None) is not None and \
                                product_producer_term.id not in validated_data['active_terms_ids']:
                                validated_data['active_terms_ids'].append(product_producer_term.id)

                else:
                    # Получаем термин корневой папки производитель
                    producer_root_tag = TermModel.objects.active().get(slug=root_producer_term_slug)
                    # Получаем термин производителя
                    product_producer_term, created = producer_root_tag.get_children().get_or_create(
                        slug=producer_guid,
                        defaults={
                            "parent_id": producer_root_tag.id,
                            "name": producer_name,
                            "semantic_rule": TermModel.OR_RULE,
                            "attributes": TermModel.attributes.is_characteristic,
                            "system_flags": _default_system_flags_restriction
                        })

                    if not created and product_producer_term.name != producer_name:
                        product_producer_term.name = producer_name
                        product_producer_term.save()

                    # устанавливаем в товар
                    instance.terms.add(product_producer_term)
                    # усли update добавляем в active_terms_ids
                    if validated_data.get('active_terms_ids', None) is not None and \
                            product_producer_term.id not in validated_data['active_terms_ids']:
                        validated_data['active_terms_ids'].append(product_producer_term.id)


        def create(self, validated_data):

            origin_validated_data = validated_data.copy()

            for key in ('transition', 'html_content', 'extra_units', 'producer'):
                validated_data.pop(key, None)

            instance = super(self.__class__, self).create(validated_data)

            self.Meta.model.RESTMeta._update_entity(self, instance, instance._is_created, origin_validated_data)


            return instance

        def update(self, instance, validated_data):

            self.Meta.model.RESTMeta._update_entity(self, instance, False, validated_data)

            return super(self.__class__, self).update(instance, validated_data)


    @property
    def entity_name(self):
        return self.product_name

    def __str__(self):
        return self.product_name


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
        if self.unit_price:
            return Decimal(self.unit_price)

        return 0.0

    @property
    def get_units(self):
        #TODO: cache
        units = self.units.all().order_by('value')
        res = []
        for unit in units:
            discount = unit.discount if unit.discount else 0.0
            res.append({
                "name": unit.name,
                "step": float(unit.value),
                "discount": float(discount),
                "price": float(self.unit_price) - float(discount)
            })
        return res

    def get_unit_by_quantity(self, quantity):
        current_unit = None

        if self.get_units:
            for unit in self.get_units:
                if unit["step"] <= quantity:
                    current_unit = unit
                else:
                    break

        return current_unit

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
            'uuid': self.uuid,
            'sku': self.get_sku,
            'product_code': self.get_product_code,
            'unit': self.get_unit,
            'step': self.get_step,
            'unit_price': self.get_unit_price,
            'is_display_price_per_step': self.get_is_display_price_per_step,
            'in_stock': self.in_stock,
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

        if not cls._meta.abstract:
            # in stock terms validation
            model_root_term = get_or_create_model_class_wrapper_term(cls)

            in_stock_parent_term, in_stock_parent_created = TermModel.objects.get_or_create(
                slug=cls.IN_STOCK_ROOT_TERM[0],
                parent=model_root_term,
                defaults={
                    'name': force_text(cls.IN_STOCK_ROOT_TERM[1]),
                    'semantic_rule': TermModel.XOR_RULE,
                    'system_flags': _default_root_terms_system_flags_restriction
                }
            )

            stock_choices = cls.IN_STOCK_CHOICES_TERMS
            for stock_key, stock_name in stock_choices:

                in_stock_choice_term, in_stock_choice_created = in_stock_parent_term.get_descendants(
                    include_self=False
                ).get_or_create(
                    slug=stock_key,
                    defaults={
                        'name': force_text(stock_name),
                        'parent_id': in_stock_parent_term.id,
                        'semantic_rule': TermModel.OR_RULE,
                        'system_flags': _full_root_terms_system_flags_restriction
                    }
                )
            # product root layout
            view_root = get_or_create_view_layouts_root()
            layout_term, layout_term_created = TermModel.objects.get_or_create(
               slug=cls.LAYOUT_TERM_SLUG,
               parent=view_root,
               defaults={
                'parent':view_root,
                'name': force_text(_('Product')),
                'semantic_rule': TermModel.XOR_RULE,
                'system_flags': _default_root_terms_system_flags_restriction
               }
            )

        super(Product, cls).validate_term_model()

    def need_terms_validation_after_save(self, origin, **kwargs):
        do_validate_layout = kwargs["context"]["validate_view_layout"] = True

        if origin is None or origin.in_stock != self.in_stock:
            kwargs["context"]["validate_in_stock"] = True

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

        if force_validate_terms or context.get("validate_in_stock", False):

            current_stock_choice = Product.IN_STOCK_CHOICES_TERMS[0] if self.in_stock and self.in_stock > 0 else Product.IN_STOCK_CHOICES_TERMS[1]

            in_stock_root_choices = getattr(Product, '_in_stock_root_choices', None)
            if in_stock_root_choices is None:
                in_stock_root_choices = {}
                try:
                    parent_wraper = get_or_create_model_class_wrapper_term(Product)
                    root = TermModel.objects.get(
                            slug=self.IN_STOCK_ROOT_TERM[0],
                            parent=parent_wraper
                        )
                    for term in root.get_descendants(include_self=True):
                        in_stock_root_choices[term.slug] = term
                except TermModel.DoesNotExist:
                    pass

                    setattr(Product, '_in_stock_root_choices', in_stock_root_choices)

            to_remove = [v for k, v in in_stock_root_choices.items() if k != current_stock_choice[0]]
            self.terms.remove(*to_remove)
            to_add = in_stock_root_choices.get(current_stock_choice[0], None)
            if to_add is not None:
                self.terms.add(to_add)

        super(Product, self).validate_terms(origin, **kwargs)


@python_2_unicode_compatible
class ProductUnit(models.Model):
    product = models.ForeignKey(
        'Product',
        verbose_name=_("Product"),
        related_name='units',
    )

    name = models.CharField(verbose_name=_('measurment unit'), max_length=50, null=False, blank=False, default='',
                            help_text=_("Additional measurement unit of product"))
    value = models.DecimalField(verbose_name=_('addition step'), default=1, max_digits=10, decimal_places=3,
                               help_text=_("conversion factor from base unit: 1 base unit * k"))
    uuid = models.CharField(verbose_name=_('measurment unit code'), max_length=50, null=False, blank=False)
    discount = models.DecimalField(verbose_name=_('discount'), default=1, max_digits=10, decimal_places=3)

    class Meta:
        app_label = app_settings.APP_LABEL
        verbose_name = _("Unit")
        verbose_name_plural = _("Units")
        unique_together = ("product", "uuid")
