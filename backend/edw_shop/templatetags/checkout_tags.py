# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from classytags.core import Tag, Options
from classytags.arguments import Argument
from django import template
from django.utils.module_loading import import_string

from edw_shop.conf import app_settings
from edw_shop.models.cart import CartModel

register = template.Library()


class RenderCheckoutForm(Tag):
    name = 'render_checkout_form'

    options = Options(
        Argument('form_name', resolve=True),
        'as',
        Argument('varname', required=True, resolve=False)
    )

    def get_cart(self, request):
        if not hasattr(self, '_cart'):
            try:
                cart = CartModel.objects.get_from_request(request)
                cart.update(request)
            except CartModel.DoesNotExist:
                cart = None
            self._cart = cart

        return self._cart

    def get_form_data(self, request, scope_prefix):
        """
        Returns data to initialize the corresponding dialog form.
        This method must return a dictionary containing
         * either `instance` - a Python object to initialize the form class for this plugin,
         * or `initial` - a dictionary containing initial form data, or if both are set, values
           from `initial` override those of `instance`.
        """

        cart = self.get_cart(request)
        res = {'cart': cart}
        if cart and cart.extra and cart.extra.get(scope_prefix, None):
            res['initial'] = cart.extra.get(scope_prefix, None)

        return res

    def get_form_class(self, scope_prefix):
        if not hasattr(self, '_checkout_form_classes'):
            self._checkout_form_classes = {}

        if hasattr(self._checkout_form_classes, scope_prefix):
            return self._checkout_form_classes.get(scope_prefix)

        for item in app_settings.DIALOG_FORMS:
            form_cls = import_string(item)
            if form_cls.scope_prefix == scope_prefix:
                self._checkout_form_classes['scope_prefix'] = form_cls

                return self._checkout_form_classes['scope_prefix']

        raise Exception("Form class with scope_prefix {} not in app_settings.DIALOG_FORMS".format(scope_prefix))

    def render_tag(self, context, form_name, varname):

        request = getattr(context, 'request', context.get('request', None))

        form_cls = self.get_form_class(form_name)
        form_data = self.get_form_data(request, form_name)

        if not isinstance(form_data.get('initial'), dict):
            form_data['initial'] = {}

        bound_form = form_cls(**form_data)

        context[varname] = bound_form

        return ''


register.tag(RenderCheckoutForm)
