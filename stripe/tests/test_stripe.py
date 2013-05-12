# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import os
import time
import unittest

import stripe
from stripe.compat import *

from . import *


class StripeTestCase(unittest.TestCase):
    def setUp(self):
        super(StripeTestCase, self).setUp()

        self.stripe = stripe.stripe     # Default Stripe instance
        api_base = os.environ.get('STRIPE_API_BASE')
        if api_base:
            self.stripe.api_base = api_base
        self.stripe.api_key = os.environ.get('STRIPE_API_KEY', 'tGN0bIwXnHdwOa85VABjPdSn8nWY7G7I')

class StripeObjectTests(StripeTestCase):
    def test_to_dict_doesnt_return_objects(self):
        invoice = self.stripe.Invoice.construct_from(SAMPLE_INVOICE, self.stripe.api_key)

        def check_object(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    check_object(k)
                    check_object(v)
            elif isinstance(obj, list):
                for v in obj:
                    check_object(v)
            else:
                self.assertFalse(isinstance(obj, stripe.StripeObject),
                                 "StripeObject %s still in to_dict result" % (repr(obj),))
        check_object(invoice.to_dict())

class JSONEncoderTests(StripeTestCase):
    def test_encoder_returns_dict(self):
        invoice = self.stripe.Invoice.construct_from(SAMPLE_INVOICE, self.stripe.api_key)
        encoded_stripe_object = stripe.StripeObjectEncoder().default(invoice)
        self.assertTrue(isinstance(encoded_stripe_object, dict),
                        "StripeObject encoded to %s" % (type(encoded_stripe_object),))

class StripeAPIRequestorTests(StripeTestCase):
    def test_builds_url_correctly_with_base_url_query_params(self):
        charges = self.stripe.Charge.all(count=5)
        paid_charges = charges.all(paid=True)
        self.assertTrue(isinstance(paid_charges.data, list))

class FunctionalTests(StripeTestCase):
    def test_dns_failure(self):
        api_base = self.stripe.api_base
        try:
            self.stripe.api_base = 'https://my-invalid-domain.ireallywontresolve/v1'
            self.assertRaises(stripe.APIConnectionError, self.stripe.Customer.create)
        finally:
            self.stripe.api_base = api_base

    def test_non_ssl(self):
        api_base = self.stripe.api_base
        try:
            self.stripe.api_base = api_base.replace('https://', 'http://')
            self.assertRaises(stripe.InsecureConnectionError, self.stripe.Customer.create)
        finally:
            self.stripe.api_base = api_base

    def test_non_ssl_suppressed(self):
        api_base = self.stripe.api_base
        suppress_non_https = self.stripe.suppress_non_https

        try:
            self.stripe.api_base = api_base.replace('https://', 'http://')
            self.stripe.suppress_non_https = True
            self.stripe.Customer.create()
        except stripe.InsecureConnectionError:
            self.fail('Insecure connection was not suppressed')
        finally:
            self.stripe.api_base = api_base
            self.stripe.suppress_non_https = suppress_non_https

    def test_run(self):
        charge = self.stripe.Charge.create(**DUMMY_CHARGE)
        self.assertFalse(charge.refunded)
        charge.refund()
        self.assertTrue(charge.refunded)

    def test_refresh(self):
        charge = self.stripe.Charge.create(**DUMMY_CHARGE)
        charge2 = self.stripe.Charge.retrieve(charge.id)
        self.assertEqual(charge2.created, charge.created)

        charge2.junk = 'junk'
        charge2.refresh()
        self.assertRaises(AttributeError, lambda: charge2.junk)

    def test_list_accessors(self):
        customer = self.stripe.Customer.create(card=DUMMY_CARD)
        self.assertEqual(customer['created'], customer.created)
        customer['foo'] = 'bar'
        self.assertEqual(customer.foo, 'bar')

    def test_raise(self):
        EXPIRED_CARD = DUMMY_CARD.copy()
        EXPIRED_CARD['exp_month'] = NOW.month - 2
        EXPIRED_CARD['exp_year'] = NOW.year - 2
        self.assertRaises(stripe.CardError, self.stripe.Charge.create, amount=100,
                          currency='usd', card=EXPIRED_CARD)

    def test_unicode(self):
        # Make sure unicode requests can be sent
        self.assertRaises(stripe.InvalidRequestError, self.stripe.Charge.retrieve, id='☃')

    def test_none_values(self):
        customer = self.stripe.Customer.create(plan=None)
        self.assertTrue(customer.id)

    def test_missing_id(self):
        customer = self.stripe.Customer()
        self.assertRaises(stripe.InvalidRequestError, customer.refresh)

class AuthenticationErrorTest(StripeTestCase):
    def test_invalid_credentials(self):
        key = self.stripe.api_key
        try:
            self.stripe.api_key = 'invalid'
            self.stripe.Customer.create()
        except stripe.AuthenticationError as e:
            self.assertEqual(401, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))
        finally:
            self.stripe.api_key = key

class CardErrorTest(StripeTestCase):
    def test_declined_card_props(self):
        EXPIRED_CARD = DUMMY_CARD.copy()
        EXPIRED_CARD['exp_month'] = NOW.month - 2
        EXPIRED_CARD['exp_year'] = NOW.year - 2
        try:
            self.stripe.Charge.create(amount=100, currency='usd', card=EXPIRED_CARD)
        except stripe.CardError as e:
            self.assertEqual(402, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))

class AccountTest(StripeTestCase):
    def test_retrieve_account(self):
        account = self.stripe.Account.retrieve()
        self.assertEqual('test+bindings@stripe.com', account.email)
        self.assertFalse(account.charge_enabled)
        self.assertFalse(account.details_submitted)

class CustomerTest(StripeTestCase):
    def test_list_customers(self):
        customers = self.stripe.Customer.all()
        self.assertTrue(isinstance(customers.data, list))

class TransferTest(StripeTestCase):
    def test_list_transfers(self):
        transfers = self.stripe.Transfer.all()
        self.assertTrue(isinstance(transfers.data, list))
        self.assertTrue(isinstance(transfers.data[0], stripe.Transfer))

    def test_list_transfers_with_queries(self):
        transfers = self.stripe.Transfer.all(count=100, date={
            'gte': 1365465600,
        })
        self.assertTrue(isinstance(transfers.data, list))
        self.assertTrue(isinstance(transfers.data[0], stripe.Transfer))

class RecipientTest(StripeTestCase):
    def test_list_recipients(self):
        recipients = self.stripe.Recipient.all()
        self.assertTrue(isinstance(recipients.data, list))
        self.assertTrue(isinstance(recipients.data[0], stripe.Recipient))

class CustomerPlanTest(StripeTestCase):
    def setUp(self):
        super(CustomerPlanTest, self).setUp()
        try:
            self.plan_obj = self.stripe.Plan.create(**DUMMY_PLAN)
        except stripe.InvalidRequestError:
            self.plan_obj = None

    def tearDown(self):
        if self.plan_obj:
            try:
                self.plan_obj.delete()
            except stripe.InvalidRequestError:
                pass
        super(CustomerPlanTest, self).tearDown()

    def test_create_customer(self):
        self.assertRaises(stripe.InvalidRequestError, self.stripe.Customer.create,
                          plan=DUMMY_PLAN['id'])
        customer = self.stripe.Customer.create(plan=DUMMY_PLAN['id'], card=DUMMY_CARD)
        self.assertTrue(hasattr(customer, 'subscription'))
        self.assertFalse(hasattr(customer, 'plan'))
        customer.delete()
        self.assertFalse(hasattr(customer, 'subscription'))
        self.assertFalse(hasattr(customer, 'plan'))
        self.assertTrue(customer.deleted)

    def test_cancel_subscription(self):
        customer = self.stripe.Customer.create(plan=DUMMY_PLAN['id'],
                                          card=DUMMY_CARD)
        customer.cancel_subscription(at_period_end=True)
        self.assertEqual(customer.subscription.status, 'active')
        self.assertTrue(customer.subscription.cancel_at_period_end)
        customer.cancel_subscription()
        self.assertEqual(customer.subscription.status, 'canceled')

    def test_datetime_trial_end(self):
        customer = self.stripe.Customer.create(plan=DUMMY_PLAN['id'], card=DUMMY_CARD,
            trial_end=datetime.datetime.now()+datetime.timedelta(days=15))
        self.assertTrue(customer.id)

    def test_integer_trial_end(self):
        trial_end_dttm = datetime.datetime.now() + datetime.timedelta(days=15)
        trial_end_int = int(time.mktime(trial_end_dttm.timetuple()))
        customer = self.stripe.Customer.create(plan=DUMMY_PLAN['id'],
                                          card=DUMMY_CARD,
                                          trial_end=trial_end_int)
        self.assertTrue(customer.id)

class CouponTest(StripeTestCase):
    def test_create_coupon(self):
        self.assertRaises(stripe.InvalidRequestError, self.stripe.Coupon.create, percent_off=25)
        c = self.stripe.Coupon.create(**DUMMY_COUPON)
        self.assertTrue(isinstance(c, stripe.Coupon))
        self.assertTrue(hasattr(c, 'percent_off'))
        self.assertTrue(hasattr(c, 'id'))

    def test_delete_coupon(self):
        c = self.stripe.Coupon.create(**DUMMY_COUPON)
        self.assertFalse(hasattr(c, 'deleted'))
        c.delete()
        self.assertFalse(hasattr(c, 'percent_off'))
        self.assertTrue(hasattr(c, 'id'))
        self.assertTrue(c.deleted)

class CustomerCouponTest(StripeTestCase):
    def setUp(self):
        super(CustomerCouponTest, self).setUp()
        self.coupon_obj = self.stripe.Coupon.create(**DUMMY_COUPON)

    def tearDown(self):
        self.coupon_obj.delete()

    def test_attach_coupon(self):
        customer = self.stripe.Customer.create(coupon=self.coupon_obj.id)
        self.assertTrue(hasattr(customer, 'discount'))
        self.assertNotEqual(None, customer.discount)

        customer.delete_discount()
        self.assertEqual(None, customer.discount)

        customer.delete()

class InvalidRequestErrorTest(StripeTestCase):
    def test_nonexistent_object(self):
        try:
            self.stripe.Charge.retrieve('invalid')
        except stripe.InvalidRequestError as e:
            self.assertEqual(404, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))

    def test_invalid_data(self):
        try:
            self.stripe.Charge.create()
        except stripe.InvalidRequestError as e:
            self.assertEqual(400, e.http_status)
            self.assertTrue(isinstance(e.http_body, basestring))
            self.assertTrue(isinstance(e.json_body, dict))

class PlanTest(StripeTestCase):
    def setUp(self):
        super(PlanTest, self).setUp()
        try:
            self.stripe.Plan(DUMMY_PLAN['id']).delete()
        except stripe.InvalidRequestError:
            pass

    def test_create_plan(self):
        self.assertRaises(stripe.InvalidRequestError, self.stripe.Plan.create, amount=2500)
        p = self.stripe.Plan.create(**DUMMY_PLAN)
        self.assertTrue(hasattr(p, 'amount'))
        self.assertTrue(hasattr(p, 'id'))
        self.assertEqual(DUMMY_PLAN['amount'], p.amount)
        p.delete()
        self.assertTrue(hasattr(p, 'deleted'))
        self.assertTrue(p.deleted)

    def test_update_plan(self):
        p = self.stripe.Plan.create(**DUMMY_PLAN)
        name = "New plan name"
        p.name = name
        p.save()
        self.assertEqual(name, p.name)
        p.delete()

    def test_update_plan_without_retrieving(self):
        p = self.stripe.Plan.create(**DUMMY_PLAN)

        name = 'updated plan name!'
        plan = self.stripe.Plan(p.id)
        plan.name = name

        self.assertEqual(sorted(['id', 'name']), sorted(plan.keys())) # should only have name and id
        plan.save()

        self.assertEqual(name, plan.name)
        self.assertEqual(p.amount, plan.amount) # should load all the properties
        p.delete()