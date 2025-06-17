from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class BlogImage(models.Model):
    _name = "blogcreator.image"
    _description = "Blog Post Images"
    _order = "sequence, id"

    name = fields.Char(string="Tiêu đề", required=False, readonly=True)
    sequence = fields.Integer(string="Số thứ tự của hình", default=1)
    image = fields.Binary(string="Hình ảnh", attachment=True, required=True)
    image_url = fields.Char(
        string="URL Hình Ảnh",
        help="URL của hình ảnh được lưu trữ trên Cloudinary.",
    )
    description = fields.Text(string="Chú thích", required=True, default="")
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
            if record.note_id and not record.is_thumbnail:
                duplicate_sequence = self.search(
                    [
                        ("note_id", "=", record.note_id.id),
                        ("sequence", "=", record.sequence),
                        ("id", "!=", record.id),
                        ("is_thumbnail", "=", False),
                    ]
                )
                if duplicate_sequence:
                    raise ValidationError(
                        _("Thứ tự (sequence) phải là duy nhất trong bài viết.")
                    )

    @api.model
    def default_get(self, fields_list):
        """
        Ghi đè phương thức default_get để đặt giá trị mặc định cho sequence.
        """
        res = super(BlogImage, self).default_get(fields_list)

        note_id = self._context.get("default_note_id")
        is_thumbnail = self._context.get("default_is_thumbnail", False)

        if note_id and "sequence" in fields_list and not is_thumbnail:
            # Tìm tất cả các số thứ tự đã sử dụng cho note_id này (trừ thumbnail)
            images = self.search(
                [("note_id", "=", note_id), ("is_thumbnail", "=", False)]
            )
            existing_sequences = images.mapped("sequence")

            # Tìm số thứ tự trống đầu tiên
            next_sequence = 1
            while next_sequence in existing_sequences:
                next_sequence += 1

            res["sequence"] = next_sequence

            if "name" in fields_list:
                res["name"] = f"Hình {next_sequence}"
        elif is_thumbnail and "name" in fields_list:
            res["name"] = "Thumbnail"
        return res

    @api.model
    def create(self, vals):
        """
        Tự động gán số thứ tự trống đầu tiên cho hình ảnh mới.
        """
        note_id = vals.get("note_id")
        is_thumbnail = vals.get("is_thumbnail", False)

        # Lấy note_id từ context nếu không có trong vals
        if not note_id and self._context.get("default_note_id"):
            note_id = self._context.get("default_note_id")
            vals["note_id"] = note_id

        if note_id and not is_thumbnail:
            # Kiểm tra xem note_id có tồn tại không
            note = self.env["blogcreator.note"].browse(note_id)
            if not note.exists():
                _logger.warning(f"CREATE - Note with ID {note_id} does not exist!")
            else:
                _logger.info(f"CREATE - Note exists with title: {note.title}")

            # Tìm tất cả các số thứ tự đã sử dụng cho note_id này (trừ thumbnail)
            images = self.search(
                [("note_id", "=", note_id), ("is_thumbnail", "=", False)]
            )
            existing_sequences = images.mapped("sequence")

            # Tìm số thứ tự trống đầu tiên
            next_sequence = 1
            while next_sequence in existing_sequences:
                next_sequence += 1

            vals["sequence"] = next_sequence
            if "name" not in vals or not vals.get("name"):
                vals["name"] = f"Hình {next_sequence}"
        elif is_thumbnail:
            # Không quan tâm đến sequence cho thumbnail
            vals["sequence"] = 0
            if "name" not in vals or not vals.get("name"):
                vals["name"] = "Thumbnail"

        result = super(BlogImage, self).create(vals)
        return result

    @api.model
    def fix_sequences(self):
        """
        Khắc phục các sequence không đúng cho tất cả image
        """
        notes = self.env["blogcreator.note"].search([])

        for note in notes:
            self._resequence_images(note.id)

        return True

    def write(self, vals):
        # Kiểm tra xem có chuyển đổi giữa thumbnail và non-thumbnail không
        need_resequence = False
        note_id_for_resequence = False

        if "is_thumbnail" in vals:
            was_thumbnail = self.is_thumbnail
            will_be_thumbnail = vals["is_thumbnail"]

            # Nếu chuyển từ non-thumbnail sang thumbnail hoặc ngược lại
            if was_thumbnail != will_be_thumbnail:
                need_resequence = True
                note_id_for_resequence = self.note_id.id

                # Nếu trở thành thumbnail, đặt sequence = 0
                if will_be_thumbnail:
                    vals["sequence"] = 0

        result = super(BlogImage, self).write(vals)

        # Nếu đánh dấu là thumbnail
        if vals.get("is_thumbnail"):
            # Tìm tất cả hình ảnh khác trong cùng note_id và thiết lập is_thumbnail = False
            other_images = self.env["blogcreator.image"].search(
                [
                    ("note_id", "=", self.note_id.id),
                    ("id", "!=", self.id),
                    ("is_thumbnail", "=", True),
                ]
            )
            if other_images:
                other_images.write({"is_thumbnail": False})

        # Sau khi cập nhật, nếu cần resequence
        if need_resequence and note_id_for_resequence:
            self._resequence_images(note_id_for_resequence)

        return result

    def unlink(self):
        """
        Ghi đè phương thức xóa để cập nhật lại số thứ tự sau khi xóa.
        """
        notes_to_resequence = {}

        # Lưu thông tin các note cần resequence
        for record in self:
            if record.note_id and not record.is_thumbnail:
                notes_to_resequence.setdefault(record.note_id.id, [])
                notes_to_resequence[record.note_id.id].append(record.sequence)

        # Thực hiện xóa record
        result = super(BlogImage, self).unlink()

        # Cập nhật lại sequence cho các note bị ảnh hưởng
        for note_id in notes_to_resequence:
            self._resequence_images(note_id)

        return result

    def _resequence_images(self, note_id):
        """
        Sắp xếp lại số thứ tự của tất cả hình ảnh trong một note.
        Chỉ đánh lại số thứ tự cho non-thumbnail images, bắt đầu từ 1.
        """

        # Chỉ lấy những ảnh không phải thumbnail
        images = self.search(
            [("note_id", "=", note_id), ("is_thumbnail", "=", False)],
            order="sequence, id",
        )

        sequence = 1
        for img in images:
            if img.sequence != sequence:
                img.write({"sequence": sequence})
            sequence += 1

        # Đảm bảo các thumbnail có sequence = 0
        thumbnails = self.search(
            [("note_id", "=", note_id), ("is_thumbnail", "=", True)]
        )

        if thumbnails:
            thumbnails.write({"sequence": 0})

    @api.onchange("is_thumbnail")
    def _onchange_is_thumbnail(self):
        """
        Khi đánh dấu là thumbnail, đặt sequence = 0.
        Khi bỏ đánh dấu thumbnail, tìm sequence tiếp theo.
        """
        if self.is_thumbnail:
            self.sequence = 0
        elif self.note_id:
            # Tìm số thứ tự trống đầu tiên cho non-thumbnail
            existing_sequences = self.search(
                [
                    ("note_id", "=", self.note_id.id),
                    ("is_thumbnail", "=", False),
                    ("id", "!=", self._origin.id if self._origin else False),
                ]
            ).mapped("sequence")

            next_sequence = 1
            while next_sequence in existing_sequences:
                next_sequence += 1

            self.sequence = next_sequence
