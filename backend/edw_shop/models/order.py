# -*- coding: utf-8 -*-
"""
Source: https://github.com/awesto/django-shop/blob/7378f024b0982ba5bf48fd07ffb18b247cba02a5/shop/models/order.py
"""
from __future__ import unicode_literals

from six import with_metaclass
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.db.models.aggregates import Sum
try:
    from django.urls import NoReverseMatch
except ImportError:
    from django.core.urlresolvers import NoReverseMatch
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _, pgettext_lazy, get_language_from_request
from django.utils.six.moves.urllib.parse import urljoin
from django.utils.encoding import force_text
from django.utils.module_loading import import_string

from rest_framework.exceptions import PermissionDenied

from django_fsm import FSMField, transition
from ipware.ip import get_ip

from edw import deferred
from edw.models.entity import EntityModel, BaseEntityManager
from edw.models.mixins.entity.fsm import FSMMixin
from edw.models.data_mart import DataMartModel
from edw.models.term import TermModel


from edw_shop.conf import app_settings
from edw_shop.models.cart import CartItemModel
from edw_shop.models.fields import JSONField
from edw_shop.money.fields import MoneyField, MoneyMaker
from .product import BaseProduct, ProductModel

_shared_system_flags_term_restriction = (
    TermModel.system_flags.delete_restriction
    | TermModel.system_flags.change_parent_restriction
    | TermModel.system_flags.change_slug_restriction
    | TermModel.system_flags.change_semantic_rule_restriction
    | TermModel.system_flags.has_child_restriction
)


_shared_system_flags_datamart_restriction = (
    DataMartModel.system_flags.delete_restriction
    | DataMartModel.system_flags.change_parent_restriction
    | DataMartModel.system_flags.change_slug_restriction
    | DataMartModel.system_flags.change_terms_restriction
)

class OrderQuerySet(models.QuerySet):
    def _filter_or_exclude(self, negate, *args, **kwargs):
        """
        Emulate filter queries on the Order model using a pseudo slug attribute.
        This allows to use order numbers as slugs, formatted by method `Order.get_number()`.
        """
        lookup_kwargs = {}
        for key, lookup in kwargs.items():
            try:
                index = key.index('__')
                field_name, lookup_type = key[:index], key[index:]
            except ValueError:
                field_name, lookup_type = key, ''
            if field_name == 'slug':
                key, lookup = self.model.resolve_number(lookup).popitem()
                lookup_kwargs.update({key + lookup_type: lookup})
            else:
                lookup_kwargs.update({key: lookup})
        return super(OrderQuerySet, self)._filter_or_exclude(negate, *args, **lookup_kwargs)


class OrderManager(BaseEntityManager):
    #_queryset_class = OrderQuerySet

    def create_from_cart(self, cart, request):
        """
        This creates a new empty Order object with a valid order number. This order is not
        populated with any cart items yet. This must be performed in the next step by calling
        ``order.populate_from_cart(cart, request)``.
        If this method is not invoked, the order object remains in state ``new``.
        """
        cart.update(request)
        cart.customer.get_or_assign_number()
        order = self.model(customer=cart.customer, _subtotal=Decimal(0), _total=Decimal(0), stored_request=self.stored_request(request))
        order.get_or_assign_number()
        order.save()
        return order

    def stored_request(self, request):
        """
        Extract useful information about the request to be used for emulating a Django request
        during offline rendering.
        """
        return {
            'language': get_language_from_request(request),
            'absolute_base_uri': request.build_absolute_uri('/'),
            'remote_ip': get_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
        }

    #todo: delete
    def filter_from_request(self, request):
        """
        Return a queryset containing the orders for the customer associated with the given
        request object.
        """
        if request.customer.is_visitor():
            detail = _("Only signed in customers can view their orders")
            raise PermissionDenied(detail=detail)
        return self.get_queryset().filter(customer=request.customer).order_by('-updated_at', )

    def get_summary_url(self):
        # """
        # Returns the URL of the page with the list view for all orders related to the current customer
        # """
        # if hasattr(self, '_summary_url'):
            # return self._summary_url
        # try:  # via CMS pages
            # page = Page.objects.public().get(reverse_id='shop-order')
        # except Page.DoesNotExist:
            # page = Page.objects.public().filter(application_urls='OrderApp').first()
        # if page:
            # self._summary_url = page.get_absolute_url()
        # else:
            # try:  # through hardcoded urlpatterns
                # self._summary_url = reverse('shop-order')
            # except NoReverseMatch:
                # self._summary_url = 'cms-page_or_view_with_reverse_id=shop-order_does_not_exist/'
        # return self._summary_url
        return "/"

    def get_latest_url(self):
        """
        Returns the URL of the page with the detail view for the latest order related to the
        current customer. This normally is the thank-you view.
        """
        return "/"



@python_2_unicode_compatible
class BaseOrder(FSMMixin, EntityModel.materialized):
    """
    An Order is the "in process" counterpart of the shopping cart, which freezes the state of the
    cart on the moment of purchase. It also holds stuff like the shipping and billing addresses,
    and keeps all the additional entities, as determined by the cart modifiers.
    """
    DATA_MART_NAME_PATTERN = '{}-dm'

    TRANSITION_TARGETS = {
        'new': _("New order"),
        'processed': _("Processed by manager"),
        'in_work': _("In work"),
        'completed': _("Completed"),
        'canceled': _("Canceled"),
    }

    VIEW_COMPONENT_LIST = 'order_list'

    VIEW_COMPONENTS = (
        (VIEW_COMPONENT_LIST, _('List')),
    )

    decimalfield_kwargs = {
        'max_digits': 30,
        'decimal_places': 2,
    }

    decimal_exp = Decimal('.' + '0' * decimalfield_kwargs['decimal_places'])

    customer = deferred.ForeignKey(
        'BaseCustomer',
        verbose_name=_("Customer"),
        related_name='orders',
    )

    status = FSMField(
        default='new',
        protected=True,
        verbose_name=_("Status"),
    )

    currency = models.CharField(
        max_length=7,
        editable=False,
        help_text=_("Currency in which this order was concluded"),
    )

    _subtotal = models.DecimalField(
        _("Subtotal"),
        **decimalfield_kwargs
    )

    _total = models.DecimalField(
        _("Total"),
        **decimalfield_kwargs
    )

    extra = JSONField(
        verbose_name=_("Extra fields"),
        help_text=_("Arbitrary information for this order object on the moment of purchase."),
    )

    stored_request = JSONField(
        verbose_name=_("Stored request"),
        help_text=_("Parts of the Request objects on the moment of purchase."),
    )

    objects = OrderManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.get_number()

    def __repr__(self):
        return "<{}(pk={})>".format(self.__class__.__name__, self.pk)

    class RESTMeta:
        lookup_fields = ('id',)

        #validators = []

        exclude = ['_subtotal', '_total', 'stored_request', 'images', 'files']

        include = {
            'subtotal': ('rest_framework.serializers.DecimalField', {
                    'max_digits': 10,
                    'decimal_places': 2,
                    'read_only': True
                }),
            'total': ('rest_framework.serializers.DecimalField', {
                'max_digits': 10,
                'decimal_places': 2,
                'read_only': True
            }),
            'amount_paid': ('rest_framework.serializers.DecimalField', {
                'max_digits': 10,
                'decimal_places': 2,
                'read_only': True
            }),
            'outstanding_amount': ('rest_framework.serializers.DecimalField', {
                'max_digits': 10,
                'decimal_places': 2,
                'read_only': True
            }), #app_settings.ORDER_ITEM_SERIALIZER
            'items': ('edw_shop.serializers.defaults.OrderItemSerializer', {
                'read_only': True,
                'many': True
            }),

            'cancelable': ('rest_framework.serializers.BooleanField', {
                'read_only': True,
            }),
            'cancel': ('rest_framework.serializers.BooleanField', {
                'write_only': True,
                'default':False,
            })

        }


    def get_summary_extra(self, context):

        extra = {
            'url': self.get_detail_url(),
            'number': self.get_number(),
            'status': self.status_name(),
            'cancelable': self.cancelable(),
            'subtotal': self.subtotal,
            'total': self.total,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        return extra


    @classmethod
    def validate_data_mart_model(cls):
        '''
        Создаем структуру витрин данных соответствующих тематической модели объектов. Модели потомки также используют
        этот метод для создания иерархии витрин данных
        :return:
        '''
        class_name = 'order'
        with transaction.atomic():
            root_cls_dm, is_created = DataMartModel.objects.get_or_create(
                slug=cls.DATA_MART_NAME_PATTERN.format(class_name),
                parent=None,
                defaults={
                    'name': force_text(cls._meta.verbose_name_plural)
                }
            )

        cls_dm = root_cls_dm

        if is_created:
            try:
                dm_term = cls.get_entities_types()[class_name]
            except KeyError:
                dm_term = cls.get_entities_types(from_cache=False)[class_name]
            cls_dm.terms.add(dm_term.id)
            cls_dm.system_flags = _shared_system_flags_datamart_restriction
            cls_dm.save()

    def get_or_assign_number(self):
        """
        Hook to get or to assign the order number. It shall be invoked, every time an Order
        object is created. If you prefer to use an order number which differs from the primary
        key, then override this method.
        """
        return self.get_number()

    def get_number(self):
        """
        Hook to get the order number.
        A class inheriting from Order may transform this into a string which is better readable.
        """
        return str(self.pk)

    @classmethod
    def resolve_number(cls, number):
        """
        Return a lookup pair used to filter down a queryset.
        It should revert the effect from the above method `get_number`.
        """
        return dict(pk=number)

    @property
    def subtotal(self):
        """
        The summed up amount for all ordered items excluding extra order lines.
        """
        # MoneyMaker(self.currency)(self._subtotal)
        return self._subtotal

    @property
    def total(self):
        """
        The final total to charge for this order.
        """
        # MoneyMaker(self.currency)(self._total)
        return self._total

    @classmethod
    def round_amount(cls, amount):
        if amount.is_finite():
            return Decimal(amount).quantize(cls.decimal_exp)

    def get_detail_url(self, data_mart=None):

        return reverse('order_detail', args=[self.pk])

    #def get_absolute_url(self, request=None, format=None):
    #    """
    #    Returns the URL for the detail view of this order.
    #    """
    #    return urljoin(OrderModel.objects.get_summary_url(), self.get_number())

    def populate_dialog_forms(self, cart, request):
        dialog_forms = set([import_string(fc) for fc in app_settings.DIALOG_FORMS])
        if dialog_forms:
            for form_class in dialog_forms:
                form_class.populate_from_cart(request, cart, self)

    @transaction.atomic
    def populate_from_cart(self, cart, request):
        """
        Populate the order object with the fields from the given cart.
        For each cart item a corresponding order item is created populating its fields and removing
        that cart item.

        Override this method, in case a customized cart has some fields which have to be transfered
        to the cart.
        """
        for cart_item in cart.items.active():
            cart_item.update(request)
            order_item = OrderItemModel(order=self)
            try:
                order_item.populate_from_cart_item(cart_item, request)
                order_item.save()
                cart_item.delete()
            except CartItemModel.DoesNotExist:
                pass

        self._subtotal = Decimal(cart.subtotal)
        self._total = Decimal(cart.total)
        self.extra = dict(cart.extra)
        self.extra.update(rows=[(modifier, extra_row.data) for modifier, extra_row in cart.extra_rows.items()])
        self.save()

        self.populate_dialog_forms(cart, request)


    @transaction.atomic
    def readd_to_cart(self, cart):
        """
        Re-add the items of this order back to the cart.
        """
        for order_item in self.items.all():
            extra = dict(order_item.extra)
            extra.pop('rows', None)
            extra.update(product_code=order_item.product_code)
            cart_item = order_item.product.is_in_cart(cart, **extra)
            if cart_item:
                cart_item.quantity = max(cart_item.quantity, order_item.quantity)
            else:
                cart_item = CartItemModel(cart=cart, product=order_item.product,
                                          product_code=order_item.product_code,
                                          quantity=order_item.quantity, extra=extra)
            cart_item.save()

    def save(self, **kwargs):
        """
        The status of an Order object may change, if auto transistions are specified.
        """
        # round the total to the given decimal_places
        self._subtotal = BaseOrder.round_amount(self._subtotal)
        self._total = BaseOrder.round_amount(self._total)
        super(BaseOrder, self).save(**kwargs)

    @cached_property
    def amount_paid(self):
        """
        The amount paid is the sum of related orderpayments
        """
        amount = self.orderpayment_set.aggregate(amount=Sum('amount'))['amount']
        if amount is None:
            amount = Decimal(0.0)#MoneyMaker(self.currency)()
        return amount

    @property
    def outstanding_amount(self):
        """
        Return the outstanding amount paid for this order
        """
        return self.total - self.amount_paid

    def is_fully_paid(self):
        return self.amount_paid >= self.total

    @transition(field='status', source='*', target='payment_confirmed', conditions=[is_fully_paid])
    def acknowledge_payment(self, by=None):
        """
        Change status to `payment_confirmed`. This status code is known globally and can be used
        by all external plugins to check, if an Order object has been fully paid.
        """

    def cancelable(self):
        """
        Returns True if the current Order is cancelable.

        This method is just a hook and must be overridden by a mixin class
        managing Order cancellations.
        """
        return False

    def refund_payment(self):
        """
        Hook to handle payment refunds.
        """

    @classmethod
    def get_all_transitions(cls):
        """
        Returns a generator over all transition objects for this Order model.
        """
        return cls.status.field.get_all_transitions(OrderModel)

    @classmethod
    def get_transition_name(cls, target):
        """Return the human readable name for a given transition target"""
        return cls.TRANSITION_TARGETS.get(target, target)

    def status_name(self):
        """Return the human readable name for the current transition state"""
        return self.TRANSITION_TARGETS.get(self.status, self.status)

    status_name.short_description = pgettext_lazy('order_models', "State")

OrderModel = deferred.MaterializedModel(BaseOrder)


@python_2_unicode_compatible
class OrderPayment(with_metaclass(deferred.ForeignKeyBuilder, models.Model)):
    """
    A model to hold received payments for a given order.
    """
    order = deferred.ForeignKey(
        BaseOrder,
        verbose_name=_("Order"),
    )

    amount = MoneyField(
        _("Amount paid"),
        help_text=_("How much was paid with this particular transfer."),
    )

    transaction_id = models.CharField(
        _("Transaction ID"),
        max_length=255,
        help_text=_("The transaction processor's reference"),
    )

    created_at = models.DateTimeField(
        _("Received at"),
        auto_now_add=True,
    )

    payment_method = models.CharField(
        _("Payment method"),
        max_length=50,
        help_text=_("The payment backend used to process the purchase"),
    )

    class Meta:
        verbose_name = pgettext_lazy('order_models', "Order payment")
        verbose_name_plural = pgettext_lazy('order_models', "Order payments")

    def __str__(self):
        return _("Payment ID: {}").format(self.id)


@python_2_unicode_compatible
class BaseOrderItem(with_metaclass(deferred.ForeignKeyBuilder, models.Model)):
    """
    An item for an order.
    """
    order = deferred.ForeignKey(
        BaseOrder,
        related_name='items',
        verbose_name=_("Order"),
    )

    product_name = models.CharField(
        _("Product name"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Product name at the moment of purchase."),
    )

    product_code = models.CharField(
        _("Product code"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Product code at the moment of purchase."),
    )

    product = deferred.ForeignKey(
        'BaseProduct',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Product"),
    )

    step = models.DecimalField(verbose_name=_('addition step'), default=1, max_digits=10, decimal_places=3)

    _unit_price = models.DecimalField(
        _("Unit price"),
        null=True,  # may be NaN
        help_text=_("Products unit price at the moment of purchase."),
        **BaseOrder.decimalfield_kwargs
    )

    _line_total = models.DecimalField(
        _("Line Total"),
        null=True,  # may be NaN
        help_text=_("Line total on the invoice at the moment of purchase."),
        **BaseOrder.decimalfield_kwargs
    )

    extra = JSONField(
        verbose_name=_("Extra fields"),
        help_text=_("Arbitrary information for this order item"),
    )

    class Meta:
        abstract = True
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")

    def __str__(self):
        return self.product_name

    @classmethod
    def perform_model_checks(cls):
        try:
            cart_field = [f for f in CartItemModel._meta.fields if f.attname == 'quantity'][0]
            order_field = [f for f in cls._meta.fields if f.attname == 'quantity'][0]
            if order_field.get_internal_type() != cart_field.get_internal_type():
                msg = "Field `{}.quantity` must be of one same type `{}.quantity`."
                raise ImproperlyConfigured(msg.format(cls.__name__, CartItemModel.__name__))
        except IndexError:
            msg = "Class `{}` must implement a field named `quantity`."
            raise ImproperlyConfigured(msg.format(cls.__name__))

    @property
    def unit_price(self):
        # MoneyMaker(self.order.currency)(self._unit_price)
        return self._unit_price

    @property
    def line_total(self):
        # MoneyMaker(self.order.currency)(self._line_total)
        return self._line_total

    def populate_from_cart_item(self, cart_item, request):
        """
        From a given cart item, populate the current order item.
        If the operation was successful, the given item shall be removed from the cart.
        If a CartItem.DoesNotExist exception is raised, discard the order item.
        """
        if cart_item.quantity == 0:
            raise CartItemModel.DoesNotExist("Cart Item is on the Wish List")

        self.product = cart_item.product
        self.product_name = cart_item.product.product_name
        self.product_code = cart_item.product_code
        self._unit_price = Decimal(cart_item.unit_price)
        self._line_total = Decimal(cart_item.line_total)
        self.quantity = cart_item.quantity
        self.step = cart_item.product.get_step
        self.extra = dict(cart_item.extra)
        extra_rows = [(modifier, extra_row.data) for modifier, extra_row in cart_item.extra_rows.items()]
        self.extra.update(rows=extra_rows)

    def save(self, *args, **kwargs):
        """
        Before saving the OrderItem object to the database, round the amounts to the given decimal places
        """
        self._unit_price = BaseOrder.round_amount(self._unit_price)
        self._line_total = BaseOrder.round_amount(self._line_total)
        super(BaseOrderItem, self).save(*args, **kwargs)


OrderItemModel = deferred.MaterializedModel(BaseOrderItem)
