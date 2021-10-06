# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from edw.views.auth import (
    LoginView as OriginalLoginView
)
from edw_shop.models.cart import CartModel


class LoginView(OriginalLoginView):
    def login(self):
        """
        Нужен для копирования корзины
        """
        try:
            anonymous_cart = CartModel.objects.get_from_request(self.request)
        except CartModel.DoesNotExist:
            anonymous_cart = None

        super(LoginView, self).login()

        if anonymous_cart is not None:
            authenticated_cart = CartModel.objects.get_from_request(self.request)
            if authenticated_cart:
                authenticated_cart.merge_with(anonymous_cart)

