import requests


class StripeError(requests.exceptions.HTTPError):
    @property
    def http_body(self):
        return self.response.text

    @property
    def http_status(self):
        return self.response.status_code

    @property
    def json_body(self):
        return self.response.json()

class APIError(StripeError):
    pass

class APIConnectionError(StripeError):
    pass

class InsecureConnectionError(APIConnectionError):
    pass

class InvalidRequestError(StripeError):
    @property
    def param(self):
        return self.response.request.params

class AuthenticationError(StripeError):
    pass

class CardError(StripeError):
    @property
    def param(self):
        return self.response.request.params

    @property
    def code(self):
        return self.response.json().get('error', {}).get('code')