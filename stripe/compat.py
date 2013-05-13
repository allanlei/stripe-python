from requests.compat import (basestring, str, urlparse, urlunparse, json, 
    quote_plus, urljoin, is_py2, is_py3)
from requests.compat import urlencode as urllib_urlencode

if is_py2:
    from urlparse import parse_qsl
elif is_py3:
    from urllib.parse import parse_qsl

import time
import datetime
import sys



def utf8(value):
    if isinstance(value, str) and sys.version_info < (3, 0):
        return value.encode('utf-8')
    return value


def urlencode(obj):
    def urlencode_list(stk, key, listvalue):
        for v in listvalue:
            v = utf8(v)
            stk.append(("%s[]" % (key), v))

    def urlencode_datetime(stk, key, dttime):
        utc_timestamp = int(time.mktime(dttime.timetuple()))
        stk.append((key, utc_timestamp))

    def urlencode_none(stk, k, v):
        pass

    def urlencode_dict(stk, key, dictvalue):
        n = {}
        for k, v in dictvalue.items():
            k, v = utf8(k), utf8(v)
            n["%s[%s]" % (key, k)] = v
        stk.extend(urlencode_inner(n))

    def urlencode_inner(obj):
        ENCODERS = {
            list: urlencode_list,
            dict: urlencode_dict,
            datetime.datetime: urlencode_datetime,
            None.__class__: urlencode_none,
        }

        stk = []
        for key, value in obj.items():
            key = utf8(key)
            try:
                encoder = ENCODERS[value.__class__]
                encoder(stk, key, value)
            except KeyError:
                # don't need special encoding
                value = utf8(value)
                stk.append((key, value))
        return stk
    return urllib_urlencode(urlencode_inner(obj))