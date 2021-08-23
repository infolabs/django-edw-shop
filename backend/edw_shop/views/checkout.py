# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/d9c1f3d4327fa23826611a57ee14fa38ec9ef51d/shop/views/checkout.py
"""
from __future__ import unicode_literals
import json

from django.db import transaction
from django.utils.module_loading import import_string

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from edw_shop.conf import app_settings
from edw_shop.models.cart import CartModel
from edw_shop.modifiers.pool import cart_modifiers_pool
from edw_shop.serializers.cart import CartSummarySerializer
#from edw_shop.serializers.checkout import CheckoutSerializer


class CheckoutViewSet(GenericViewSet):
    """
    View for our REST endpoint to communicate with the various forms used during the checkout.
    """
    serializer_label = 'checkout'
    serializer_class = CartSummarySerializer
    cart_serializer_class = CartSummarySerializer

    def __init__(self, **kwargs):
        super(CheckoutViewSet, self).__init__(**kwargs)
        self.dialog_forms = set([import_string(fc) for fc in app_settings.DIALOG_FORMS])


    @action(detail=False, methods=['put'], url_path='upload')
    def upload(self, request):
        """
        Use this REST endpoint to upload the payload of all forms used to setup the checkout
        dialogs. This method takes care to dispatch the uploaded payload to each corresponding
        form.
        """
        # sort posted form data by plugin order
        cart = CartModel.objects.get_from_request(request)

        dialog_data = []
        for form_class in self.dialog_forms:

            if form_class.scope_prefix in request.data.keys():
                dialog_data.append((form_class, request.data[form_class.scope_prefix]))
                #for data in request.data[form_class.scope_prefix].values():
                #   dialog_data.append((form_class, data))
        #dialog_data = sorted(dialog_data, key=lambda tpl: int(tpl[1]['plugin_order']))

        # save data, get text representation and collect potential errors
        errors, response_data, set_is_valid = {}, {}, True

        with transaction.atomic():
            for form_class, data in dialog_data:
                form = form_class.form_factory(request, data, cart)
                if form.is_valid():
                    # empty error dict forces revalidation by the client side validation
                    errors[form_class.form_name] = {}
                else:
                    errors[form_class.form_name] = form.errors
                    set_is_valid = False

                # by updating the response data, we can override the form's content
                update_data = form.get_response_data()
                if isinstance(update_data, dict):
                    response_data[form.form_name] = update_data

            # persist changes in cart
            if set_is_valid:
                cart.save()

        # add possible form errors for giving feedback to the customer
        if set_is_valid:
            return Response(response_data)
        else:
            return Response(errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    @action(detail=False, methods=['get'], url_path='digest')
    def digest(self, request):
        #TODO:
        """
        Returns the summaries of the cart and various checkout forms to be rendered in non-editable fields.
        """
        cart = CartModel.objects.get_from_request(request)
        cart.update(request)
        context = self.get_serializer_context()
        #checkout_serializer = self.serializer_class(cart, context=context, label=self.serializer_label)
        cart_serializer = self.cart_serializer_class(cart, context=context, label='cart')
        response_data = {
            #'checkout_digest': checkout_serializer.data,
            'cart_summary': cart_serializer.data,
        }
        return Response(data=response_data)


    @action(detail=False, methods=['post'], url_path='purchase')
    def purchase(self, request):

        # TODO:
        """
        This is the final step on converting a cart into an order object. It normally is used in
        combination with the plugin :class:`shop.cascade.checkout.ProceedButtonPlugin` to render
        a button labeled "Purchase Now".
        """
        cart = CartModel.objects.get_from_request(request)
        cart.update(request)
        cart.save()

        response_data = {}
        # Iterate over the registered modifiers, and search for the active payment service provider
        for modifier in cart_modifiers_pool.get_payment_modifiers():
            if modifier.is_active(cart):
                payment_provider = getattr(modifier, 'payment_provider', None)
                if payment_provider:
                    expression = payment_provider.get_payment_request(cart, request)
                    response_data.update(expression=expression)
                break
        return Response(data=response_data)
