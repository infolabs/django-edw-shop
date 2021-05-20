# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.forms.forms import Form


class BaseDialogForm(Form):
    scope_prefix = 'dialog_form' # uniq id
    legend = _("Dialog Form Base")

    def __init__(self, *args, **kwargs):
        cart = kwargs.pop('cart', None)
        super(BaseDialogForm, self).__init__(*args, **kwargs)

    def has_choices(self):
        return False

    @classmethod
    def form_factory(cls, request, data, cart):

        cart.update(request)
        form = cls(data=data, cart=cart)
        if form.is_valid():
            cdata = {form.form_name: form.cleaned_data}
            cart.extra.update(cdata)

        return form

    @property
    def form_name(self):
        return self.scope_prefix

    def get_response_data(self):
        #TODO: base response
        return {}