# -*- coding: utf-8 -*-

from flectra import models, fields, api


class Towns(models.Model):
    _name = 'hr_pf.officetown'
    name = fields.Char(string='Офисы в Городах')


class HrEmployeePf(models.Model):
    _inherit = 'hr.employee'
    # Поля для синхронизации с ПФ
    id_pf = fields.Integer(string='id Глобальный')
    general_user_pf = fields.Integer(string='id в адр.строке')
    userid_pf = fields.Integer(string='id для задач')
    general_contact_pf = fields.Integer(string='id в адр.строке')
    officetown_id = fields.Many2one('hr_pf.officetown', string='Офис и Город')
    # Добавляем аналог  department_id - projectgroup_id. Для этого проводим рефакторинг по ключам:
    # 'department_id', 'hr.department', 'Department'
