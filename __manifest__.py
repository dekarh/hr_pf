# -*- coding: utf-8 -*-
{
    'name': "hr_pf",

    'summary': """
        Импорт данных и дополнительные поля для модулей hr для сохранения связей с данными из ПланФикса 
    """,

    'description': """
        Импорт данных и дополнительные поля для модулей hr для сохранения связей с данными из ПланФикса
    """,

    'author': "Денис Алексеев",
    'website': "https://github.com/dekarh",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/flectra/flectra/blob/master/flectra/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.0.16',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'users_pf'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/pf_views.xml',
        'data/hr_pf_data.xml',
        'data/res.users.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}