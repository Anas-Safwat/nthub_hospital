{
    'name': 'Hospital System',
    'version': '19.0.0.1.0',
    'description': 'This module simulates a hospital system for booking appointments with doctors and handling the related workflows.',
    'author': 'Anas Ibrahim',
    'license': 'LGPL-3',
    'depends': [
        'base','account','hr','stock','mail','contacts','calendar','resource','appointment'
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/rules.xml",
        "security/security.xml",
        "views/hospital_appointment_views.xml",
        "views/hospital_clinic_views.xml",
        "views/hospital_department_views.xml",
        "views/hospital_doctor_views.xml",
        "views/hospital_menus.xml",
        "views/hospital_nurse_views.xml",
        "views/hospital_patient_views.xml",
        "views/hospital_reciptionist_views.xml",
        "views/appointment_type_views.xml",
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': True,
    'assets': {
    }
}