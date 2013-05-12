import logging

from ..errors import InvalidRequestError
from ..utils import utf8, convert_to_stripe_object
from ..encoders import JSONEncoder
from ..compat import *

logger = logging.getLogger('stripe')



class StripeObject(object):
    _permanent_attributes = set(['stripe', 'resource_uri'])
    stripe = None
    resource_uri = None

    def __init__(self, id=None, stripe=None, **params):
        self.__dict__['_values'] = set()
        self.__dict__['_unsaved_values'] = set()
        self.__dict__['_transient_values'] = set()
        self.__dict__['_retrieve_params'] = params
        self.stripe = stripe or self.__class__.stripe

        if id:
            self.id = id
            self.resource_uri = '{base}/{id}'.format(
                base=self.__class__.resource_uri,
                id=quote_plus(utf8(id)))
        else:
            self.resource_uri = None

    def __setattr__(self, k, v):
        self.__dict__[k] = v
        self._values.add(k)
        if k not in self._permanent_attributes:
            self._unsaved_values.add(k)

    def __getattr__(self, k):
        try:
            return self.__dict__[k]
        except KeyError:
            pass
        if k in self._transient_values:
            raise AttributeError("%r object has no attribute %r.  HINT: The %r attribute was set in the past, however.  It was then wiped when refreshing the object with the result returned by Stripe's API, probably as a result of a save().  The attributes currently available on this object are: %s" %
                    (type(self).__name__, k, k, ', '.join(self._values)))
        else:
            raise AttributeError("%r object has no attribute %r" % (type(self).__name__, k))

    def __getitem__(self, k):
        if k in self._values:
            return self.__dict__[k]
        elif k in self._transient_values:
            raise KeyError("%r.  HINT: The %r attribute was set in the past, however.  It was then wiped when refreshing the object with the result returned by Stripe's API, probably as a result of a save().  The attributes currently available on this object are: %s" % (k, k, ', '.join(self._values)))
        else:
            raise KeyError(k)

    def get(self, k, default=None):
        try:
            return self[k]
        except KeyError:
            return default

    def setdefault(self, k, default=None):
        try:
            return self[k]
        except KeyError:
            self[k] = default
        return default

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    @classmethod
    def construct_from(cls, values, stripe=None):
        stripe = stripe or cls.stripe
        instance = cls(values.get('id'), stripe=stripe)
        instance.refresh_from(values)
        return instance

    def refresh_from(self, values, partial=False):
        # Wipe old state before setting new.  This is useful for e.g. updating a
        # customer, where there is no persistent card parameter.  Mark those values
        # which don't persist as transient
        if partial:
            removed = set()
        else:
          removed = self._values - set(values)

        for k in removed:
            if k in self._permanent_attributes:
                continue
            del self.__dict__[k]
            self._values.discard(k)
            self._transient_values.add(k)
            self._unsaved_values.discard(k)

        for k, v in values.items():
            if k in self._permanent_attributes:
                continue
            self.__dict__[k] = convert_to_stripe_object(v, stripe=self.stripe)
            self._values.add(k)
            self._transient_values.discard(k)
            self._unsaved_values.discard(k)

    def __repr__(self):
        type_string = ''
        if isinstance(self.get('object'), basestring):
            type_string = ' %s' % self.get('object').encode('utf8')

        id_string = ''
        if isinstance(self.get('id'), basestring):
            id_string = ' id=%s' % self.get('id').encode('utf8')

        return '<%s%s%s at %s> JSON: %s' % (type(self).__name__, type_string, id_string, hex(id(self)), json.dumps(self.to_dict(), sort_keys=True, indent=2, cls=JSONEncoder))

    def __unicode__(self):
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, cls=JSONEncoder)

    def to_dict(self):
        def _serialize(o):
            if isinstance(o, StripeObject):
                return o.to_dict()
            if isinstance(o, list):
                return [_serialize(i) for i in o]
            return o

        d = dict()
        for k in sorted(self._values):
            if k in self._permanent_attributes:
                continue
            v = getattr(self, k)
            v = _serialize(v)
            d[k] = v
        return d




class APIResource(StripeObject):
    def _ident(self):
        return [self.get('id')]

    @classmethod
    def retrieve(cls, id, stripe=None, **params):
        stripe = stripe or cls.stripe
        instance = cls(id, stripe=stripe, **params)
        instance.refresh()
        return instance

    def refresh(self):
        requestor = self.stripe

        if not self.resource_uri:
            id = self.get('id')
            raise InvalidRequestError('Could not determine which URL to request: %s instance has invalid ID: %r' % (type(self).__name__, id), 'id')
        response = requestor.request('get', self.resource_uri, params=self._retrieve_params)
        self.refresh_from(response)
        return self


class ListObject(StripeObject):
    def all(self, **params):
        requestor = self.stripe
        response = requestor.request('get', self.resource_uri, params=params)
        return convert_to_stripe_object(response, stripe=self.stripe)

class SingletonAPIResource(APIResource):
    def __init__(self, *args, **kwargs):
        super(SingletonAPIResource, self).__init__(*args, **kwargs)
        self.resource_uri = self.__class__.resource_uri

    def _ident(self):
        return [self.get('id')]

    @classmethod
    def retrieve(cls, stripe=None):
        stripe = stripe or cls.stripe
        instance = cls(None, stripe=stripe)
        instance.refresh()
        return instance




# Classes of API operations
class ListableAPIResource(APIResource):
    @classmethod
    def all(cls, stripe=None, **params):
        stripe = stripe or cls.stripe
        requestor = stripe
        response = requestor.request('get', cls.resource_uri, params=params)
        list_obj = convert_to_stripe_object(response, stripe=stripe)
        list_obj.resource_uri = cls.resource_uri
        return list_obj

class CreateableAPIResource(APIResource):
    @classmethod
    def create(cls, stripe=None, **params):
        stripe = stripe or cls.stripe
        requestor = stripe
        response = requestor.request('post', cls.resource_uri, data=params)
        return convert_to_stripe_object(response, stripe=stripe)

class UpdateableAPIResource(APIResource):
    def save(self):
        if self._unsaved_values:
            requestor = self.stripe

            params = {}
            for k in self._unsaved_values:
                if k == 'id':
                    continue
                params[k] = getattr(self, k)

            response = requestor.request('post', self.resource_uri, data=params)
            self.refresh_from(response)
        else:
            logger.debug("Trying to save already saved object %r" % (self, ))
        return self

class DeletableAPIResource(APIResource):
    def delete(self, **params):
        requestor = self.stripe
        response = requestor.request('delete', self.resource_uri, params=params)
        self.refresh_from(response)
        return self