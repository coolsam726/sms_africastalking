{
    'name': 'Africastalking SMS',
    'version': '1.0',
    'summary': 'Send SMS messages using Africastalking',
    'category': 'Hidden/Tools',
    'description': """
This module allows using Africastalking as a provider for SMS messaging.
The user has to create an account on africastalking.com and top
up their account to start sending SMS messages. This is especially suitable for African Countries.
""",
    'depends': [
        'sms',
        'sms_twilio'
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sms_sms_views.xml',
        'wizard/sms_africastalking_account_manage_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'author': 'Savannabits Ltd.',
    'license': 'LGPL-3',
}
