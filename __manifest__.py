# -*- coding: utf-8 -*-
{
    'name': "hr_pf",

    'summary': """
        Дополнительные поля для модулей hr для сохранения связей с данными из ПланФикса 
    """,

    'description': """
        Дополнительные поля для модулей hr Flectra(odoo) для сохранения связей с данными из ПланФикса 
    """,

    'author': "Денис Алексеев",
    'website': "https://github.com/dekarh",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/flectra/flectra/blob/master/flectra/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.0.5',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_views.xml',
        'data/hr_employee_pf_data.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}