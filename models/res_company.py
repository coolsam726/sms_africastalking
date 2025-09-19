import re

from odoo import fields, models, _
from odoo.exceptions import UserError

from ..tools.sms_api import SmsApiAfricastalking


class ResCompany(models.Model):
    _inherit = 'res.company'

    sms_provider = fields.Selection(
        selection_add=[
            ('africastalking', 'Send via Africastalking'),
        ],
    )
    sms_at_username = fields.Char("Africastalking Username", groups='base.group_system')
    sms_at_shortcode = fields.Char("Africastalking Shortcode", groups='base.group_system')
    sms_at_api_key = fields.Char("Africastalking API Key", groups='base.group_system')

    def _get_sms_api_class(self):
        self.ensure_one()
        if self.sms_provider == 'africastalking':
            return SmsApiAfricastalking
        return super()._get_sms_api_class()

    def _assert_at_username(self):
        self.ensure_one()
        account_sid = self.sms_at_username

        # Ensure alphanumeric no pecial characters
        if not re.match(r'^[a-zA-Z0-9]+$', account_sid):
            raise UserError(_("The Africastalking Username must be alphanumeric without special characters."))

    def _action_open_sms_at_account_manage(self):
        return {
            'name': _('Manage Africastalking SMS'),
            'res_model': 'sms.africastalking.account.manage',
            'res_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
        }
