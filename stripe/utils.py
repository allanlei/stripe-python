from .compat import *


def convert_to_stripe_object(resp, stripe=None):
    """
    Initializes a StripeObject from a JSON response
    """
    from .api import (Charge, Customer, Invoice, InvoiceItem, Plan, 
        Coupon, Token, Event, Transfer, ListObject, Recipient, StripeObject)

    types = {
        'charge': Charge, 
        'customer': Customer,
        'invoice' : Invoice, 
        'invoiceitem' : InvoiceItem,
        'plan': Plan, 
        'coupon': Coupon, 
        'token': Token, 
        'event': Event,
        'transfer': Transfer, 
        'list': ListObject, 
        'recipient': Recipient,
    }

    if isinstance(resp, list):
        return [convert_to_stripe_object(i, stripe=stripe) for i in resp]
    elif isinstance(resp, dict):
        resp = resp.copy()
        klass_name = resp.get('object')
        if isinstance(klass_name, basestring):
            klass = types.get(klass_name, StripeObject)
        else:
            klass = StripeObject
        klass.stripe = stripe
        return klass.construct_from(resp)
    else:
        return resp