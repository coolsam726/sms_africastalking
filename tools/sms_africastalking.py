import base64
import hashlib
import hmac

from odoo.tools.urls import urljoin

from odoo.addons.phone_validation.tools import phone_validation

def get_at_status_callback_url(company, uuid):
    base_url = company.get_base_url()  # When testing locally, this should be replaced by a real url (not localhost, e.g. with ngrok)
    return urljoin(base_url, f'/sms_africastalking/status/{uuid}')


def generate_at_sms_callback_signature(company, sms_uuid, callback_params):
    url = get_at_status_callback_url(company, sms_uuid)
    # Sort the POST parameters by key and concatenate them to URL
    sorted_params = ''.join(f"{k}{v}" for k, v in sorted(callback_params.items()))
    data = url + sorted_params

    # Compute HMAC-SHA1 digest and then base64 encode
    return base64.b64encode(
        hmac.new(
            company.sms_at_api_key.encode(),
            data.encode(),
            hashlib.sha1
        ).digest()
    ).decode()
