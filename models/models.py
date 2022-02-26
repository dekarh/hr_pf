# -*- coding: utf-8 -*-

from flectra import models, fields, api

class towns(models.Model):
    _name = 'hr_pf.officetown'
    name = fields.Char(string='Офисы в Городах')

class hr_employee_pf(models.Model):
    _inherit = 'hr.employee'
    id_pf = fields.Integer(string='id Глобальный')
    general_user_pf = fields.Integer(string='id в адр.строке')
    userid_pf = fields.Integer(string='id для задач')
    general_contact_pf = fields.Integer(string='id в адр.строке')
    officetown_id = fields.Many2one('hr_pf.officetown',string='Офис и Город')

