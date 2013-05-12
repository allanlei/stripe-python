import logging

from .base import *

logger = logging.getLogger('stripe')



class Account(SingletonAPIResource):
    resource_uri = '/account'

class Charge(CreateableAPIResource, ListableAPIResource, UpdateableAPIResource):
    resource_uri = '/charges'

    def refund(self, **params):
        requestor = self.stripe
        response = requestor.request('post', self.resource_uri + '/refund', data=params)
        self.refresh_from(response)
        return self

    def capture(self, **params):
        requestor = self.stripe
        response = requestor.request('post', self.resource_uri + '/capture', data=params)
        self.refresh_from(response)
        return self

    def update_dispute(self, **params):
        requestor = self.stripe
        response = requestor.request('post', self.resource_uri + '/dispute', data=params)
        self.refresh_from({ 'dispute' : response }, True)
        return self.dispute

class Customer(CreateableAPIResource, UpdateableAPIResource, ListableAPIResource, DeletableAPIResource):
    resource_uri = '/customers'

    def add_invoice_item(self, **params):
        params['customer'] = self.id
        ii = InvoiceItem.create(**params)
        return ii

    def invoices(self, **params):
        params['customer'] = self.id
        invoices = Invoice.all(stripe=self.stripe, **params)
        return invoices

    def invoice_items(self, **params):
        params['customer'] = self.id
        iis = InvoiceItem.all(stripe=self.stripe, **params)
        return iis

    def charges(self, **params):
        params['customer'] = self.id
        charges = Charge.all(stripe=self.stripe, **params)
        return charges

    def update_subscription(self, **params):
        requestor = self.stripe
        response = requestor.request('post', self.resource_uri + '/subscription', data=params)
        self.refresh_from({ 'subscription' : response }, True)
        return self.subscription

    def cancel_subscription(self, **params):
        requestor = self.stripe
        response = requestor.request('delete', self.resource_uri + '/subscription', data=params)
        self.refresh_from({ 'subscription' : response }, True)
        return self.subscription

    def delete_discount(self, **params):
        requestor = self.stripe
        response = requestor.request('delete', self.resource_uri + '/discount')
        self.refresh_from({ 'discount' : None }, True)

class Invoice(CreateableAPIResource, ListableAPIResource, UpdateableAPIResource):
    resource_uri = '/invoices'

    def pay(self):
        from .utils import convert_to_stripe_object
        requestor = self.stripe
        response, = requestor.request('post', self.resource_uri + '/pay', data={})
        return convert_to_stripe_object(response, stripe=stripe)

    @classmethod
    def upcoming(cls, stripe=None, **params):
        stripe = stripe or cls.stripe
        from .utils import convert_to_stripe_object
        requestor = stripe
        response = requestor.request('get', cls.resource_uri + '/upcoming', params=params)
        return convert_to_stripe_object(response, stripe=stripe)

class InvoiceItem(CreateableAPIResource, UpdateableAPIResource, ListableAPIResource, DeletableAPIResource):
    resource_uri = '/invoiceitems'

class Plan(CreateableAPIResource, DeletableAPIResource, UpdateableAPIResource, ListableAPIResource):
    resource_uri = '/plans'

class Token(CreateableAPIResource):
    resource_uri = '/tokens'

class Coupon(CreateableAPIResource, DeletableAPIResource, ListableAPIResource):
    resource_uri = '/coupons'

class Event(ListableAPIResource):
    resource_uri = '/events'

class Transfer(CreateableAPIResource, ListableAPIResource):
    resource_uri = '/transfers'

class Recipient(CreateableAPIResource, UpdateableAPIResource, ListableAPIResource, DeletableAPIResource):
    resource_uri = '/recipients'

    def transfers(self, **params):
        params['recipient'] = self.id
        transfers = Transfer.all(stripe=self.stripe, **params)
        return transfers