# -*- coding: utf-8 -*-
from rest_framework import serializers
from django.core import exceptions
from django.core.cache import cache
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.utils.html import strip_spaces_between_tags
from django.utils import six
from django.utils.safestring import mark_safe, SafeText
from django.utils.translation import get_language_from_request

from edw_shop.models.product import ProductModel
from edw_shop.conf import app_settings

from edw.rest.serializers.entity import EntitySummarySerializer

class ProductUnitSerializer(serializers.Serializer):
    """
    A serializer to additional units.
    """
    name = serializers.CharField(required=True, max_length=50)
    value = serializers.DecimalField(max_digits=10, decimal_places=3, required=True)
    discount = serializers.DecimalField(max_digits=10, decimal_places=3, required=False)
    uuid = serializers.CharField(required=True, max_length=50)


class ProductGroupPropertySerializer(serializers.Serializer):
    default_root = serializers.CharField(required=True, max_length=50)
    guid = serializers.CharField(required=True, max_length=50)
    name = serializers.CharField(required=True, max_length=255)
    parent_guid = serializers.CharField(required=True, max_length=50)
    parent_name = serializers.CharField(required=True, max_length=255)
    categories = serializers.ListField(
        required=False,
        child=serializers.CharField(required=True, max_length=50)
    )


class ProductSerializer(serializers.ModelSerializer):
    """
    Common serializer for our product model.
    """
    price = serializers.DecimalField(source='get_unit_price', max_digits=10, decimal_places=3, read_only=True)
    availability = serializers.SerializerMethodField()
    product_type = serializers.CharField(read_only=True)
    product_model = serializers.CharField(read_only=True)
    product_url = serializers.URLField(source='get_absolute_url', read_only=True)
    detail_url = serializers.CharField(read_only=True, source='get_detail_url')
    units = serializers.ListField(source='get_units', read_only=True)
    media = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'catalog')
        super(ProductSerializer, self).__init__(*args, **kwargs)

    def get_price(self, product):
        #TODO: not used with request
        price = product.get_price(self.context['request'])
        # TODO: check if this can be simplified using str(product.get_price(...))
        if six.PY2:
            return u'{:f}'.format(price)
        return '{:f}'.format(price)

    def get_availability(self, product):
        return product.get_availability(self.context['request'])

    def get_media(self, entity):
        return self.render_html(entity, 'media')

    def render_html(self, product, postfix):
        """
        Return a HTML snippet containing a rendered summary for this product.
        Build a template search path with `postfix` distinction.
        """
        if not self.label:
            msg = "The Product Serializer must be configured using a `label` field."
            raise exceptions.ImproperlyConfigured(msg)
        app_label = product._meta.app_label.lower()
        request = self.context['request']
        cache_key = 'product:{0}|{1}-{2}-{3}-{4}-{5}'.format(product.id, app_label, self.label,
            product.product_model, postfix, get_language_from_request(request))
        content = cache.get(cache_key)
        if content:
            return mark_safe(content)
        params = [
            (app_label, self.label, product.product_model, postfix),
            (app_label, self.label, 'product', postfix),
            ('shop', self.label, 'product', postfix),
        ]
        try:
            template = select_template(['{0}/products/{1}-{2}-{3}.html'.format(*p) for p in params])
        except TemplateDoesNotExist:
            return SafeText("<!-- no such template: '{0}/products/{1}-{2}-{3}.html' -->".format(*params[0]))
        # when rendering emails, we require an absolute URI, so that media can be accessed from
        # the mail client
        absolute_base_uri = request.build_absolute_uri('/').rstrip('/')
        context = {'product': product, 'ABSOLUTE_BASE_URI': absolute_base_uri}
        content = strip_spaces_between_tags(template.render(context, request).strip())
        cache.set(cache_key, content, app_settings.CACHE_DURATIONS['product_html_snippet'])
        return mark_safe(content)