from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class BlogImage(models.Model):
    _name = "blogcreator.image"
    _description = "Blog Post Images"
    _order = "sequence, id"

    name = fields.Char(string="Tiêu đề", required=True)
    sequence = fields.Integer(string="Thứ tự", default=1)
    image = fields.Binary(string="Hình ảnh", attachment=True, required=True)
    image_url = fields.Char(
        string="URL Hình Ảnh",
        help="URL của hình ảnh được lưu trữ trên Cloudinary.",
    )
    description = fields.Text(string="Mô tả")
    note_id = fields.Many2one(
        "blogcreator.note", string="Blog Post", ondelete="cascade"
    )
    is_thumbnail = fields.Boolean(
        string="Thumbnail",
        default=False,
        help="Đánh dấu hình ảnh này là thumbnail cho bài viết.",
    )

    @api.depends("is_thumbnail", "note_id.image_ids")
    def _get_thumbnail_url(self):
        """
        Automatically fetch the thumbnail URL from associated images.
        """
        thumbnail_img = self.note_id.image_ids.filtered(lambda img: img.is_thumbnail)
        if thumbnail_img:
            return thumbnail_img[0].image_url
        return None

    @api.constrains("sequence", "note_id")
    def _check_unique_sequence(self):
        """
        Ensure that sequence values are unique within a note.
        """
        for record in self:
            if record.note_id:
                duplicate_sequence = self.search(
                    [
                        ("note_id", "=", record.note_id.id),
                        ("sequence", "=", record.sequence),
                        ("id", "!=", record.id),
                    ]
                )
                if duplicate_sequence:
                    raise ValidationError(
                        _("Thứ tự (sequence) phải là duy nhất trong bài viết.")
                    )

    @api.onchange("is_thumbnail")
    def _onchange_is_thumbnail(self):
        """
        Ensure only one image is marked as thumbnail within a note.
        """
        if self.is_thumbnail:
            for img in self.note_id.image_ids:
                if img.id != self.id:
                    img.is_thumbnail = False

    @api.model
    def create(self, vals):
        """
        Automatically assign sequence and thumbnail status for new images.
        """
        note_id = vals.get("note_id")
        if note_id:
            # Find the maximum sequence in note_id
            existing_images = self.search(
                [("note_id", "=", note_id)], order="sequence desc"
            )
            if existing_images:
                max_sequence = existing_images[0].sequence
                vals["sequence"] = max_sequence + 1
                vals["is_thumbnail"] = False  # Không tự động đánh dấu là thumbnail
            else:
                # Nếu không có hình ảnh nào, đây là hình ảnh đầu tiên
                vals["sequence"] = 1
                vals["is_thumbnail"] = True  # Tự động đánh dấu là thumbnail
        else:
            # Default sequence and thumbnail if no note_id
            vals["sequence"] = 1
            vals["is_thumbnail"] = True

        return super(BlogImage, self).create(vals)

    def write(self, vals):
        """
        Ensure thumbnail logic when updating records.
        """
        if vals.get("is_thumbnail"):
            # Nếu hình ảnh này được đánh dấu là thumbnail, bỏ đánh dấu các hình ảnh khác
            for img in self.note_id.image_ids:
                if img.id != self.id:
                    img.is_thumbnail = False
        return super(BlogImage, self).write(vals)
