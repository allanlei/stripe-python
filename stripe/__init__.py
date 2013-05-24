# -*- coding: utf-8 -*-
"""
Stripe Python bindings
~~~~~~~~~~~~~~~~~~~~~~

stripe-requests is a replacement for stripe-python using only the requests 
library. Basic usage:

   >>> from stripe import Stripe
   >>> stripe = Stripe(api_key='MY_API_KEY')
   >>> stripe.Account.retrieve()

Full documentation is at <https://stripe-requests.readthedocs.org>.

:copyright: (c) 2013 by Allan Lei.
:license: MIT, see LICENSE for more details.

"""

__title__ = 'stripe-requests'
__version__ = '1.9.1-dev'
__author__ = 'Allan Lei'
__license__ = 'MIT'
__copyright__ = 'Copyright 2013 Allan Lei'


import os
import platform
import logging
import requests

from .compat import *
from .transport import OAuth2Auth, HTTPAdapter
from .encoders import JSONEncoder
from .errors import *
from .api import *

__all__ = ['StripeObject', 'Charge', 'Coupon', 'Plan', 'Transfer', 'Recipient', 
    'JSONEncoder', 'StripeObjectEncoder', 'StripeError', 'APIError', 'APIConnectionError', 
    'InvalidRequestError', 'AuthenticationError', 'CardError', 'stripe', 'Stripe']

StripeObjectEncoder = JSONEncoder

STRIPE_CONNECT_URL = 'https://connect.stripe.com/oauth/token'
STRIPE_API_BASE_V1 = 'https://api.stripe.com/v1/'
STRIPE_API_BASE = STRIPE_API_BASE_V1

logger = logging.getLogger('stripe')


class Stripe(object):
    @classmethod
    def from_code(cls, code, client_id, client_secret_key, grant_type='authorization_code'):
        """
        Trade a Stripe Connect code for the user's Stripe API keys.
        """
        response = requests.post(STRIPE_CONNECT_URL, 
            auth=OAuth2Auth(client_secret_key), 
            params={
                'grant_type': grant_type, 
                'client_id': client_id, 
                'code': code,
            })
        return cls(api_key=response.json()['access_token'])

    def __init__(self, api_key=None, verify_ssl_certs=True, api_version=None, 
            api_base=STRIPE_API_BASE, session_class=requests.Session):
        super(Stripe, self).__init__()
        self.session = session_class()
        self.session.mount('http://', HTTPAdapter())
        self.session.mount('https://', HTTPAdapter())
        self.session.auth = OAuth2Auth()
        self.api_key = api_key
        self.verify_ssl_certs = verify_ssl_certs
        self.api_version = api_version
        self.api_base = api_base

        self.session.headers.update({
            'User-Agent' : 'stripe-requests/{version}'.format(version=__version__),
            'X-Stripe-Client-User-Agent' : json.dumps({
                'bindings_version' : __version__,
                'lang': 'python',
                'implementation': platform.python_implementation(),
                'publisher' : 'stripe',
                'httplib': requests.__title__,
                'lang_version': platform.python_version(),
                'platform': platform.platform(),
                'uname': ' '.join(platform.uname()),
            }),
        })

        # TODO: This is weird, mainly to keep the interface the same as stripe-python
        for res in [
            'Account',
            'Charge',
            'Customer',
            'Invoice',
            'InvoiceItem',
            'Plan',
            'Token',
            'Coupon',
            'Event',
            'Transfer',
            'Recipient']:
            Resource = type(res, (globals()[res], ), {
                'stripe': self,
            })
            setattr(self, res, Resource)

    def request(self, method, url, *args, **kwargs):
        if 'api_key' in kwargs:
            kwargs.setdefault('auth', OAuth2Auth(kwargs.pop('api_key')))
        url = urljoin(self.api_base, url)

        data = kwargs.get('data', None)
        if data and not isinstance(data, basestring):
            kwargs['data'] = urlencode(data)

        params = kwargs.get('params', None)
        if params and not all([isinstance(value, (basestring, int)) for value in params.values()]):
            url_parts = list(urlparse(url))
            query = dict(parse_qsl(url_parts[4]))
            query.update(kwargs.pop('params'))
            url_parts[4] = urlencode(query)
            url = urlunparse(url_parts)

        try:
            response = self.session.request(method, url, *args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            raise InsecureConnectionError(str(e))
        except requests.exceptions.RequestException as e:
            # Reraise as APIConnectionError
            raise APIConnectionError(str(e))

        response.raise_for_status()
        return response.json()

    @property
    def api_key(self):
        return self.session.auth.api_key

    @api_key.setter
    def api_key(self, key):
        self.session.auth.api_key = key

    @property
    def verify_ssl_certs(self):
        return bool(self.session.verify)

    @verify_ssl_certs.setter
    def verify_ssl_certs(self, verify):
        self.session.verify = bool(verify)

    @property
    def api_version(self):
        return self.session.headers.get('Stripe-Version', None)

    @api_version.setter
    def api_version(self, version):
        if not version:
            return
        self.session.headers.update({
            'Stripe-Version': version,
        })


# A default Stripe instance, api_key from env var
stripe = Stripe(api_key=os.environ.get('STRIPE_API_KEY'))