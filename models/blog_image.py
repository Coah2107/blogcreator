from odoo import models, fields, api


class BlogImage(models.Model):
    _name = "blogcreator.image"
    _description = "Blog Post Images"
    _order = "sequence, id"

    name = fields.Char(string="Tiêu đề", required=True)
    sequence = fields.Integer(string="Thứ tự", default=10)
    image = fields.Binary(string="Hình ảnh", attachment=True, required=True)
    description = fields.Text(string="Mô tả")
    note_id = fields.Many2one(
        "blogcreator.note", string="Blog Post", ondelete="cascade"
    )
