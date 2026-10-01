{
    'name': 'Hospital System',
    'version': '19.0.0.1.0',
    'description': 'This module simulates a hospital system for booking appointments with doctors and handling the related workflows.',
    'author': 'Anas Ibrahim',
    'license': 'LGPL-3',
    'depends': [
        'base','account','hr','stock','mail','contacts'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
    ],
    'demo': [
        ''
    ],
    'auto_install': False,
    'application': False,
    'assets': {
        
    }
}