# -*- coding: utf-8 -*-

from flectra import models, fields, api
from flectra import tools, _
from flectra.exceptions import ValidationError, AccessError
from flectra.modules.module import get_module_resource


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
    projectgroup_id = fields.Many2one('hr.projectgroup', string='ProjectGroup')

    @api.onchange('projectgroup_id')
    def _onchange_projectgroup(self):
        self.parent_id = self.projectgroup_id.manager_id


class HrJobPf(models.Model):
    _inherit = 'hr.job'
    projectgroup_id = fields.Many2one('hr.projectgroup', string='ProjectGroup')


class ProjectGroup(models.Model):
    _name = "hr.projectgroup"
    _description = "ProjectGroup"
    _inherit = ['mail.thread']
    _order = "name"

    name = fields.Char(string='ProjectGroup', required=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    parent_id = fields.Many2one('hr.projectgroup', string='Parent ProjectGroup', index=True)
    child_ids = fields.One2many('hr.projectgroup', 'parent_id', string='Child ProjectGroup')
    manager_id = fields.Many2one('hr.projectgroup', string='Manager', track_visibility='onchange')
    member_ids = fields.One2many('hr.employee', 'projectgroup_id', string='Members', readonly=True)
    jobs_ids = fields.One2many('hr.job', 'projectgroup_id', string='Jobs')
    note = fields.Text('Note')
    color = fields.Integer('Color Index')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for projectgroup in self:
            if projectgroup.parent_id:
                projectgroup.complete_name = '%s / %s' % (projectgroup.parent_id.complete_name, projectgroup.name)
            else:
                projectgroup.complete_name = projectgroup.name

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive projectgroups.'))

    @api.model
    def create(self, vals):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        projectgroup = super(ProjectGroup, self.with_context(mail_create_nosubscribe=True)).create(vals)
        manager = self.env['hr.employee'].browse(vals.get("manager_id"))
        if manager.user_id:
            projectgroup.message_subscribe_users(user_ids=manager.user_id.ids)
        return projectgroup

    @api.multi
    def write(self, vals):
        """ If updating manager of a projectgroup, we need to update all the employees
            of projectgroup hierarchy, and subscribe the new manager.
        """
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if 'manager_id' in vals:
            manager_id = vals.get("manager_id")
            if manager_id:
                manager = self.env['hr.employee'].browse(manager_id)
                # subscribe the manager user
                if manager.user_id:
                    self.message_subscribe_users(user_ids=manager.user_id.ids)
            # set the employees's parent to the new manager
            self._update_employee_manager(manager_id)
        return super(ProjectGroup, self).write(vals)

    def _update_employee_manager(self, manager_id):
        employees = self.env['hr.employee']
        for projectgroup in self:
            employees = employees | self.env['hr.employee'].search([
                ('id', '!=', manager_id),
                ('projectgroup_id', '=', projectgroup.id),
                ('parent_id', '=', projectgroup.manager_id.id)
            ])
        employees.write({'parent_id': manager_id})




