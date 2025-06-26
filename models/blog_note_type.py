# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class BlogNoteType(models.Model):
    _name = "blogcreator.note.type"
    _description = "Blog Note Type"
    _rec_name = "name"
    _order = "sequence, id"

    name = fields.Char(string="Tên hiển thị", required=True, translate=True)
    code = fields.Char(string="Mã", required=True)
    sequence = fields.Integer(string="Thứ tự", default=10)
    prompt = fields.Text(string="Prompt", required=True, translate=True, 
                         help="Hướng dẫn về phong cách và tone viết")
    active = fields.Boolean(string="Active", default=True)
    
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Mã thể loại phải là duy nhất!')
    ]