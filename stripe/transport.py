import requests

from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers
from requests.cookies import extract_cookies_to_jar

from . import errors



class OAuth2Auth(requests.auth.AuthBase):
    def __init__(self, api_key=None):
        self.api_key = api_key

    def __call__(self, req):
        if self.api_key:
            req.headers['Authorization'] = 'Bearer {api_key}'.format(
                api_key=self.api_key)
        return req


class Response(requests.models.Response):
    def raise_for_status(self):
        HTTPErrorClass = errors.StripeError
        http_error_msg = ''
        error = {}

        if 400 <= self.status_code < 500:
            http_error_msg = '%s Client Error: %s' % (self.status_code, self.reason)

        elif 500 <= self.status_code < 600:
            http_error_msg = '%s Server Error: %s' % (self.status_code, self.reason)

        try:
            error = self.json()['error']
        except KeyError:
            pass

        if self.status_code in [requests.codes.bad_request, requests.codes.not_found]:
            HTTPErrorClass, http_error_msg = errors.InvalidRequestError, error.get('message')
        elif self.status_code in [requests.codes.unauthorized]:
            HTTPErrorClass, http_error_msg = errors.AuthenticationError, error.get('message')
        elif self.status_code in [requests.codes.payment_required]:
            HTTPErrorClass, http_error_msg = errors.CardError, error.get('message')
        elif self.status_code in [requests.codes.forbidden]:
            if not self.request.url.startswith('https://'):
                HTTPErrorClass, http_error_msg = errors.InsecureConnectionError, 'Insecure connection'

        if http_error_msg and HTTPErrorClass:
            raise HTTPErrorClass(http_error_msg, response=self)


class HTTPAdapter(requests.adapters.HTTPAdapter):
    def build_response(self, req, resp):
        """
        Copy of requests.adapters.HTTPAdapter(1.9.1). 
        Overriding to use a custom Response class
        """
        response = Response()

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(resp, 'status', None)

        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(getattr(resp, 'headers', {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self
        return response