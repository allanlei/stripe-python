from .compat import json


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        from .api import StripeObject
        
        if isinstance(obj, StripeObject):
            return obj.to_dict()
        return super(JSONEncoder, self).default(obj)