import logging
import requests

from odoo import _, fields, models
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms_twilio.tools.sms_twilio import get_twilio_from_number
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SmsAfricastalkingAccountManage(models.TransientModel):
    _name = 'sms.africastalking.account.manage'
    _description = 'SMS Africastalking Connection Wizard'

    company_id = fields.Many2one(comodel_name='res.company', required=True, readonly=True, default=lambda self: self.env.company)
    sms_provider = fields.Selection(related='company_id.sms_provider', readonly=False)
    sms_at_username = fields.Char(related='company_id.sms_at_username', readonly=False)
    sms_at_shortcode = fields.Char(related='company_id.sms_at_shortcode', readonly=False)
    sms_at_api_key = fields.Char(related='company_id.sms_at_api_key', readonly=False)
    test_number = fields.Char("Test Number")

    def action_send_test(self):
        if not self.test_number:
            raise UserError(_("Please set the number to which you want to send a test SMS."))
        composer = self.env['sms.composer'].create({
            'body': _("This is a test SMS from Odoo"),
            'composition_mode': 'numbers',
            'numbers': self.test_number,
        })
        sms_su = composer._action_send_sms()[0]

        has_error = bool(sms_su.failure_type)
        if not has_error:
            message = _("The SMS has been sent from %s", get_twilio_from_number(self.company_id.sudo(), self.test_number).display_name)
        elif sms_su.failure_type != "unknown":
            sms_api = self.company_id._get_sms_api_class()(self.env)
            failure_type = dict(self.env['sms.sms']._fields['failure_type'].get_description(self.env)['selection']).get(sms_su.failure_type, sms_su.failure_type)
            message = _('%(failure_type)s: %(failure_reason)s',
                         failure_type=failure_type,
                         failure_reason=sms_api._get_sms_api_error_messages().get(sms_su.failure_type, failure_type),
            )
        else:
            message = _("Error: %s", sms_su.failure_type)
        return self._display_notification(
            notif_type='danger' if has_error else 'success',
            message=message,
        )

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}

    def _display_notification(self, notif_type, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Africastalking SMS"),
                'message': message,
                'type': notif_type,
                'sticky': False,
            }
        }
