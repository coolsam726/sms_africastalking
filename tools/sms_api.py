import logging

import africastalking
import requests
from africastalking.Service import AfricasTalkingException

from odoo import _
from odoo.addons.sms.tools import sms_api
from odoo.exceptions import ValidationError
from .sms_africastalking import get_at_status_callback_url

_logger = logging.getLogger(__name__)


class SmsApiAfricastalking(sms_api.SmsApiBase):
    PROVIDER_TO_SMS_FAILURE_TYPE = sms_api.SmsApiBase.PROVIDER_TO_SMS_FAILURE_TYPE | {
        'at_acc_unverified' : 'sms_acc',
        'at_authentication' : 'sms_credit',
        'at_callback'       : 'at_callback',
        'at_from_missing'   : 'at_from_missing',
        'at_from_to'        : 'at_from_to',
    }
    AT_SMS = None  # Will be set in __init__
    company_sudo = None  # Will be set in __init__
    def __init__(self, env, account=None):
        super().__init__(env, account=account)
        company_sudo = (self.company or self.env.company).sudo()
        if company_sudo.sms_provider == 'africastalking':
            company_sudo._assert_at_username()
            self.company_sudo = company_sudo
            try:
                africastalking.initialize(company_sudo.sms_at_username, company_sudo.sms_at_api_key)
                self.AT_SMS = africastalking.SMS
            except AfricasTalkingException as e:
                # Show a notification toast message
                _logger.warning('Africastalking SMS API initialization error: %s', str(e))
                raise ValidationError("Africastalking SMS client could not be initialized: %s", str(e))
            except requests.exceptions.RequestException as e:
                _logger.warning('Africastalking SMS API initialization error: %s', str(e))
                raise ValidationError("Africastalking SMS client could not be initialized: %s", str(e))

    def _sms_at_send_request(self, session, to_number, body, uuid):
        if not self.company_sudo:
            raise ValueError("Africastalking SMS configuration is missing")
        if not self.AT_SMS:
            raise ValueError("Africastalking SMS client could not be initialized")
        company_sudo = self.company_sudo
        sender = company_sudo.sms_at_shortcode
        recipients = [to_number]
        try:
            response = self.AT_SMS.send(body,recipients,sender)
            _logger.info('Raw response from Africastalking SMS API: %s', response)
            return self._at_get_sms_response_payload(response)
        except AfricasTalkingException as e:
            _logger.warning('Africastalking SMS API error: %s', str(e))
            return {
                'error_message': str(e),
                'status_code': 500,
                'status': 'InternalServerError',
            }
        except requests.exceptions.RequestException as e:
            _logger.warning('Africastalking SMS API error: %s', str(e))
            return {
                'error_message': str(e),
                'status_code': 500,
                'status': 'InternalServerError',
            }

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        """ Send a batch of SMS using Africastalking.
        See params and returns in original method sms/tools/sms_api.py
        In addition to the uuid and state, we add the sms_at_sid to the returns (one per sms)
        """
        # Use a session as we have to sequentially call twilio, might save time
        session = requests.Session()

        res = []
        for message in messages:
            body = message.get('content') or ''
            for number_info in message.get('numbers') or []:
                uuid = number_info['uuid']
                response = self._sms_at_send_request(session, number_info['number'], body, uuid)
                fields_values = {
                    'failure_reason':  _("Unknown failure at sending, please contact Odoo support"),
                    'state': 'server_error',
                    'uuid': uuid,
                }
                if response is not None:
                    response_json = response
                    if response_json.get('error_message') or response_json.get('error'):
                        failure_type = self._at_error_code_to_odoo_state(response_json)
                        error_message = response_json.get('message') or response_json.get('error_message') or self._get_sms_api_error_messages().get(failure_type)
                        fields_values.update({
                            'failure_reason': error_message,
                            'failure_type': failure_type,
                            'state': failure_type,
                        })
                    else:
                        fields_values.update({
                            'failure_reason': False,
                            'failure_type': False,
                            'sms_at_sid': response_json.get('sms_at_sid'),
                            'state': 'sent',
                        })
                res.append(fields_values)
        return res

    def _at_error_code_to_odoo_state(self, response_json):
        error_code = response_json.get('code') or response_json.get('status_code') or response_json.get('error_code')
        # number issues
        if error_code in (500, 501, 502):  # See https://www.twilio.com/docs/errors/xxxxx
            return "at_gateway_error"
        elif error_code == 401:
            # A "To" phone number is required
            return "at_risk_hold"
        elif error_code == 402:
            return "at_invalid_sender_id"
        elif error_code == 403:
            return "at_invalid_phone_number"
        # configuration
        elif error_code == 404:
            return "at_unsupported_number_type"
        elif error_code == 405:
            return "at_insufficient_balance"
        elif error_code == 406:
            return "at_user_in_blacklist"
        elif error_code == 407:
            return "at_could_not_route"
        elif error_code == 407:
            return "at_do_not_disturb_rejection"
        _logger.warning('Africastalking SMS: Unknown error "%s" (code: %s)', response_json.get('message'), error_code)
        return "unknown"

    def _get_sms_api_error_messages(self):
        # TDE TODO: clean failure type management
        error_dict = super()._get_sms_api_error_messages()
        error_dict.update({
            'at_gateway_error': _("Africastalking gateway error, please retry later"),
            'at_risk_hold': _("Africastalking account is on risk hold, please contact Africastalking support"),
            'at_invalid_sender_id': _("Africastalking invalid sender ID, please check your configuration"),
            'at_invalid_phone_number': _("Africastalking invalid phone number"),
            'at_unsupported_number_type': _("Africastalking unsupported phone number type"),
            'at_insufficient_balance': _("Africastalking insufficient balance, please top-up your account"),
            'at_user_in_blacklist': _("Africastalking user in blacklist, message cannot be sent"),
            'at_could_not_route': _("Africastalking could not route the message to the destination"),
            'at_do_not_disturb_rejection': _("Africastalking message rejected due to Do Not Disturb settings"),
            'at_callback': _("Africastalking callback URL issue, please check your configuration"),  # not used for now
            'at_from_missing': _("Africastalking missing From number, please check your configuration"),
            'at_from_to': _("Africastalking From and To numbers cannot be the same"),
            'at_authentication': _("Africastalking authentication error, please check your API key"),
            'at_acc_unverified': _("Africastalking account unverified, please verify your account"),
            'at_sms_credit': _("Africastalking SMS credit error, please check your account balance"),
            # fallback
            'unknown': _("Unknown error, please contact Odoo support"),
        })
        return error_dict

    def _at_get_sms_response_payload(self, response):
        # In the format
        # {
        #     "SMSMessageData": {
        #         "Message": "Sent to 1/1 Total Cost: KES 0.8000",
        #         "Recipients": [{
        #             "statusCode": 101,
        #             "number": "+254711XXXYYY",
        #             "status": "Success",
        #             "cost": "KES 0.8000",
        #             "messageId": "ATPid_SampleTxnId123"
        #         }]
        #     }
        # }

        # We just need the payload of the first recipient

        payload = response.get('SMSMessageData', {}).get('Recipients', [])
        if not payload or not isinstance(payload, list) or not payload[0]:
            _logger.warning("Africastalking SMS: No recipient information in response: %s", response)
            return {
                'error_message': _("Africastalking SMS: No recipient information in response"),
                'status_code': 500,
                'status': 'InternalServerError',
            }
        payload = payload[0]
        # Extract cost as the float after the space in "KES 0.8000"
        cost_string = payload.get('cost')
        if cost_string and isinstance(cost_string, str) and ' ' in cost_string:
            try:
                cost = float(cost_string.split(' ')[1])
            except ValueError:
                cost = None
        if cost_string and isinstance(cost_string, str) and ' ' in cost_string:
            currency = cost_string.split(' ')[0]
        else:
            currency = None
        return {
            'status_code': payload.get('statusCode'),
            'sms_at_sid': payload.get('messageId'),
            'recipient_number': payload.get('number'),
            'status': payload.get('status'),
            'cost': cost,
            'currency_code': currency,
        }