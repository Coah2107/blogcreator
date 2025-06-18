# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import base64
from bs4 import BeautifulSoup
import re
import traceback
from io import BytesIO

_logger = logging.getLogger(__name__)


class BlogNote(models.Model):
    _name = "blogcreator.note"
    _description = "Blog Notes for n8n Integration"
    _rec_name = "title"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # Thêm tính năng chatter

    title = fields.Char(string="Tiêu đề", required=True, tracking=True)
    content = fields.Html(string="Nội dung", tracking=True)
    note_type = fields.Selection(
        [
            ("general", "Chọn Thể Loại"),
            ("culinary", "Ẩm Thực"),
            ("entertainment", "Giải Trí"),
            ("wellness_healing", "Sức Khỏe & Thư Giãn"),
            ("adventure", "Phiêu Lưu & Khám Phá"),
            ("family_friendly", "Gia Đình"),
            ("insta_worthy", "Sống Ảo & Check-in"),
            ("eco_friendly", "Du Lịch Xanh & Bền Vững"),
            ("coworking_remote", "Làm Việc & Đồng Hành"),
            ("shopping_spree", "Mua Sắm & Giải Trí"),
            ("arts_exhibition", "Nghệ Thuật & Triển Lãm"),
            ("spa_relaxation", "Spa & Thư Giãn"),
            ("street_food", "Ẩm Thực Đường Phố"),
            ("hidden_gems", "Điểm Đến Bí Ẩn"),
            ("photography_spot", "Điểm Chụp Ảnh"),
        ],
        string="Thể Loại",
        default="general",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("exported", "Đã tạo bài viết tự động"),
            ("approved", "Đã duyệt"),
        ],
        string="Trạng thái",
        default="draft",
        tracking=True,
    )
    is_published = fields.Boolean(string="Đã duyệt", default=False, tracking=True)
    exported_to_n8n = fields.Boolean(
        string="Đã tạo bài viết tự động", default=False, tracking=True
    )
    export_date = fields.Datetime(string="Ngày xuất", readonly=True)
    tags = fields.Char(
        string="Hashtag", help="Các tag cách nhau bởi dấu phẩy", tracking=True
    )
    user_id = fields.Many2one(
        "res.users",
        string="Người tạo",
        default=lambda self: self.env.user,
        readonly=True,
    )

    image = fields.Binary(
        string="Hình ảnh chính",
        attachment=True,
        help="Hình ảnh sẽ được hiển thị ở đầu bài viết",
    )
    image_ids = fields.One2many("blogcreator.image", "note_id", string="Hình ảnh")

    n8n_response_ids = fields.One2many(
        "blogcreator.n8n.response", "note_id", string="N8n Responses"
    )

    last_n8n_response_id = fields.Many2one(
        "blogcreator.n8n.response",
        string="Latest Response",
        compute="_compute_last_response",
        store=True,
    )
    last_n8n_status = fields.Integer(
        related="last_n8n_response_id.status_code", string="Latest Status", store=False
    )
    last_n8n_success = fields.Boolean(
        related="last_n8n_response_id.success", string="Latest Success", store=False
    )

    @api.depends("n8n_response_ids")
    def _compute_last_response(self):
        for record in self:
            record.last_n8n_response_id = self.env["blogcreator.n8n.response"].search(
                [("note_id", "=", record.id)], order="response_time desc", limit=1
            )

    def _get_thumbnail_url(self):
        thumbnail_img = self.image_ids.filtered(lambda img: img.is_thumbnail)
        if thumbnail_img:
            return thumbnail_img[0].image_url
        elif self.image_ids:
            return self.image_ids[0].image_url
        return None

    # @api.constrains("is_published", "exported_to_n8n")
    # def _check_state_changes(self):
    #     """Cập nhật state khi is_published hoặc exported_to_n8n thay đổi"""
    #     for record in self:
    #         if record.exported_to_n8n and record.state != "exported":
    #             record.state = "exported"
    #         elif (
    #             record.is_published
    #             and not record.exported_to_n8n
    #             and record.state != "approved"
    #         ):
    #             record.state = "approved"
    #         elif (
    #             not record.is_published
    #             and not record.exported_to_n8n
    #             and record.state != "draft"
    #         ):
    #             record.state = "draft"

    # def update_state(self):
    #     for record in self:
    #         current_state = record.state
    #         if record.exported_to_n8n:
    #             new_state = "exported"
    #         elif record.is_published:
    #             new_state = "approved"
    #         else:
    #             new_state = "draft"

    #         if current_state != new_state:
    #             record._write({"state": new_state})
    #     return True

    # def mark_as_exported(self):
    #     """Đánh dấu note đã được xuất sang n8n"""
    #     for record in self:
    #         record.write(
    #             {
    #                 "exported_to_n8n": True,
    #                 "export_date": fields.Datetime.now(),
    #             }
    #         )
    #         record.update_state()
    #         record.message_post(body="Đã xuất thành công sang n8n")
    #     return True

    def export_to_n8n(self):
        """Hàm chuẩn bị và xuất dữ liệu sang n8n"""
        self.ensure_one()

        if self.state != "draft":
            raise UserError("Chỉ có thể tạo bài viết từ trạng thái nháp!")

        try:
            import re as regex

            # Khởi tạo biến debug_exceptions
            debug_exceptions = []
            cloudinary_utils = self.env["blogcreator.cloudinary.utils"]

            # Thêm logs để debug
            _logger.info(
                f"Starting export_to_n8n for blog: {self.title} (ID: {self.id})"
            )
            _logger.info(f"Image field exists: {hasattr(self, 'image')}")
            _logger.info(f"Image field has value: {bool(self.image)}")

            # Lấy URL webhook từ system parameters
            webhook_url = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("blogcreator.n8n_webhook_url")
            )

            if not webhook_url:
                raise Exception(
                    "URL webhook n8n chưa được cấu hình. Vui lòng thiết lập tham số 'blogcreator.n8n_webhook_url'"
                )

            # Khởi tạo danh sách để lưu các URL hình ảnh từ Cloudinary
            cloudinary_images = []
            main_cloudinary_image = None

            # Xử lý hình ảnh chính (nếu có)
            if self.image:
                try:
                    # Upload hình ảnh chính lên Cloudinary
                    _logger.info("Uploading main image to Cloudinary")
                    _logger.info(f"Image type: {type(self.image)}")

                    # Chuyển đổi dữ liệu hình ảnh sang định dạng phù hợp
                    image_data = self.image
                    if not isinstance(image_data, str):
                        # Nếu image_data là bytes, chuyển đổi sang base64 string
                        _logger.info("Converting binary image data to base64")
                        image_data = (
                            base64.b64encode(image_data).decode("utf-8")
                            if isinstance(image_data, bytes)
                            else image_data
                        )

                    # Chuẩn bị tên public_id từ tiêu đề bài viết
                    blog_title_slug = regex.sub(
                        r"[^a-zA-Z0-9_]", "_", self.title.lower()
                    )
                    public_id = f"blog_{self.id}_{blog_title_slug}_main"

                    # Upload lên Cloudinary sử dụng class mới
                    response = cloudinary_utils.upload_to_cloudinary(
                        image_data,
                        public_id=public_id,
                        folder="blog_creator/main_images",
                    )

                    if response and response.get("secure_url"):
                        main_cloudinary_image = response["secure_url"]
                        _logger.info(
                            f"Main image uploaded to Cloudinary: {main_cloudinary_image}"
                        )

                        # Thêm hình ảnh chính vào danh sách hình ảnh
                        cloudinary_images.append(
                            {
                                "url": main_cloudinary_image,
                                "alt": self.title,
                                "width": response.get("width"),
                                "height": response.get("height"),
                                "is_main": True,
                            }
                        )

                except Exception as e:
                    error_msg = str(e)
                    _logger.error(
                        f"Error uploading main image to Cloudinary: {error_msg}"
                    )
                    _logger.exception("Exception details:")
                    debug_exceptions.append(
                        {
                            "location": "main_image",
                            "error": error_msg,
                            "traceback": traceback.format_exc(),
                        }
                    )

            # Xử lý hình ảnh trong HTML content
            html_content = self.content or ""

            _logger.info(f"Content field has value: {bool(html_content)}")
            if html_content:
                _logger.info(f"Content length: {len(html_content)}")
                _logger.info(f"Content preview: {html_content[:100]}...")

                plain_text_content = ""

                try:
                    soup = BeautifulSoup(html_content, "html.parser")

                    paragraphs = soup.find_all(
                        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]
                    )
                    plain_text_parts = []

                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text:
                            plain_text_parts.append(text)

                    plain_text_content = "\n\n".join(plain_text_parts)

                    if not plain_text_content:
                        plain_text_content = soup.get_text(separator="\n\n", strip=True)

                    _logger.info(
                        f"Plain text content extracted: {plain_text_content[:100]}..."
                    )

                    img_tags = soup.find_all("img")
                    _logger.info(f"Found {len(img_tags)} img tags in HTML content")

                    # Tạo một phiên bản mới của soup để chỉnh sửa
                    new_soup = BeautifulSoup(html_content, "html.parser")
                    new_img_tags = new_soup.find_all("img")

                    for i, img_tag in enumerate(img_tags):
                        src = img_tag.get("src", "")
                        if not src:
                            _logger.warning(f"Image {i+1} has empty src attribute")
                            continue

                        _logger.info(f"Processing image {i+1} with src: {src}")

                        try:
                            # Xử lý URL nội bộ Odoo
                            if src.startswith("/web/"):
                                _logger.info("Internal Odoo URL detected")
                                base_url = (
                                    self.env["ir.config_parameter"]
                                    .sudo()
                                    .get_param("web.base.url")
                                )
                                full_url = f"{base_url}{src}"
                                _logger.info(
                                    f"Converting internal URL to full URL: {full_url}"
                                )
                                src = full_url

                            # Sinh một public_id duy nhất cho mỗi hình ảnh
                            image_public_id = f"blog_{self.id}_content_image_{i+1}"

                            # Upload hình ảnh lên Cloudinary
                            response = cloudinary_utils.upload_to_cloudinary(
                                src,
                                public_id=image_public_id,
                                folder="blog_creator/content_images",
                            )

                            # Lấy secure URL từ Cloudinary
                            cloudinary_url = response.get("secure_url")
                            _logger.info(f"Cloudinary URL: {cloudinary_url}")

                            # Lưu thông tin hình ảnh để gửi đến n8n
                            cloudinary_images.append(
                                {
                                    "url": cloudinary_url,
                                    "original_url": src,
                                    "alt": img_tag.get("alt", ""),
                                    "width": response.get("width"),
                                    "height": response.get("height"),
                                }
                            )

                            # Cập nhật src trong HTML mới
                            new_img_tags[i]["src"] = cloudinary_url
                            _logger.info(
                                f"Updated image {i+1} with Cloudinary URL: {cloudinary_url}"
                            )
                        except Exception as e:
                            error_msg = str(e)
                            _logger.error(f"Error processing image {i+1}: {error_msg}")
                            _logger.exception("Exception details:")
                            debug_exceptions.append(
                                {
                                    "location": f"content_image_{i+1}",
                                    "src": src,
                                    "error": error_msg,
                                    "traceback": traceback.format_exc(),
                                }
                            )
                            # Giữ nguyên URL cũ nếu có lỗi
                            cloudinary_images.append(
                                {
                                    "url": src,
                                    "alt": img_tag.get("alt", ""),
                                    "error": str(e),
                                }
                            )

                    # Cập nhật nội dung HTML với các URL Cloudinary mới
                    _logger.info("HTML content updated with Cloudinary URLs")
                except Exception as e:
                    error_msg = str(e)
                    _logger.error(f"Error processing HTML content: {error_msg}")
                    _logger.exception("Exception details:")
                    debug_exceptions.append(
                        {
                            "location": "html_content",
                            "error": error_msg,
                            "traceback": traceback.format_exc(),
                        }
                    )
            else:
                _logger.info("No HTML content to process")
                plain_text_content = ""

            # Xử lý hình ảnh từ image_ids nếu có
            image_ids_details = []
            if hasattr(self, "image_ids") and self.image_ids:
                _logger.info(f"Found {len(self.image_ids)} images in image_ids")
                for idx, img_record in enumerate(self.image_ids):
                    # Thêm debug info cho từng record
                    record_info = {
                        "index": idx,
                        "has_image_attr": hasattr(img_record, "image"),
                        "image_value_exists": (
                            bool(img_record.image)
                            if hasattr(img_record, "image")
                            else False
                        ),
                        "record_id": (
                            img_record.id if hasattr(img_record, "id") else None
                        ),
                        "record_name": (
                            img_record.name if hasattr(img_record, "name") else None
                        ),
                        "is_thumbnail": (
                            img_record.is_thumbnail
                            if hasattr(img_record, "is_thumbnail")
                            else False
                        ),
                    }
                    image_ids_details.append(record_info)

                    if hasattr(img_record, "image") and img_record.image:
                        try:
                            _logger.info(f"Processing gallery image {idx+1}")
                            _logger.info(f"Image type: {type(img_record.image)}")
                            # Chuyển đổi dữ liệu hình ảnh sang định dạng phù hợp
                            image_data = img_record.image

                            # Tải lên Cloudinary
                            image_public_id = f"blog_{self.id}_gallery_image_{idx+1}"

                            # Sử dụng class mới
                            is_thumbnail = (
                                hasattr(img_record, "is_thumbnail")
                                and img_record.is_thumbnail
                            )
                            response = cloudinary_utils.upload_to_cloudinary(
                                image_data,
                                public_id=image_public_id,
                                folder="blog_creator/gallery_images",
                                is_thumbnail=is_thumbnail,
                            )

                            # Thêm vào danh sách hình ảnh
                            cloudinary_images.append(
                                {
                                    "url": response.get("secure_url"),
                                    "alt": (
                                        img_record.name
                                        if hasattr(img_record, "name")
                                        else f"Gallery image {idx+1}"
                                    ),
                                    "description": (
                                        img_record.description
                                        if hasattr(img_record, "description")
                                        and img_record.description
                                        else ""
                                    ),
                                    "width": response.get("width"),
                                    "height": response.get("height"),
                                    "is_gallery": True,
                                    "is_thumbnail": is_thumbnail,
                                    "sequence": img_record.sequence,
                                }
                            )

                            # Cập nhật URL trên record
                            img_record.image_url = response.get("secure_url")
                            _logger.info(f"Gallery image {idx+1} uploaded successfully")

                        except Exception as e:
                            error_msg = str(e)
                            _logger.error(
                                f"Error uploading gallery image {idx+1}: {error_msg}"
                            )
                            _logger.exception("Exception details:")
                            debug_exceptions.append(
                                {
                                    "location": f"gallery_image_{idx+1}",
                                    "error": error_msg,
                                    "traceback": traceback.format_exc(),
                                }
                            )
            else:
                _logger.info("No gallery images found")

            content_images = []
            for img in cloudinary_images:
                content_images.append(
                    {
                        "url": img.get("url"),
                        "caption": img.get("description", ""),
                        "key": img.get("alt"),
                    }
                )

            thumbnail_url = self._get_thumbnail_url()

            if thumbnail_url and content_images:
                # Tìm hình ảnh có URL trùng với thumbnail_url
                thumbnail_image = next(
                    (img for img in content_images if img.get("url") == thumbnail_url),
                    None,
                )
                if thumbnail_image:
                    # Loại bỏ thumbnail khỏi content_images
                    content_images.remove(thumbnail_image)
                    _logger.info(
                        f"Removed thumbnail from content_images: {thumbnail_image['url']}"
                    )

            # Chuẩn bị dữ liệu để xuất
            export_data = {
                "id": self.id,
                "title": self.title,
                "content": plain_text_content,
                "note_type": dict(self._fields["note_type"].selection).get(
                    self.note_type
                ),
                "tags": self.tags,
                "is_published": self.is_published,
                "create_date": fields.Datetime.to_string(self.create_date),
                "user": self.env.user.name,
                "thumbnail": thumbnail_url,
                "content_images": content_images,
            }

            include_debug = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("blogcreator.include_debug_info", "True")
                .lower()
                == "true"
            )

            if include_debug:
                export_data["debug_info"] = {
                    "has_main_image": bool(self.image),
                    "main_image_type": str(type(self.image)) if self.image else None,
                    "has_img_tags": (
                        len(soup.find_all("img"))
                        if "soup" in locals() and html_content
                        else 0
                    ),
                    "image_ids_count": (
                        len(self.image_ids) if hasattr(self, "image_ids") else 0
                    ),
                    "cloudinary_config": {
                        "cloud_name": self.env["ir.config_parameter"]
                        .sudo()
                        .get_param("blogcreator.cloudinary_cloud_name", "Not set"),
                        "has_api_key": bool(
                            self.env["ir.config_parameter"]
                            .sudo()
                            .get_param("blogcreator.cloudinary_api_key")
                        ),
                    },
                    "exceptions": debug_exceptions,
                    "image_ids_details": image_ids_details,
                }

            # Gửi dữ liệu tới n8n qua webhook
            response = requests.post(
                webhook_url,
                json=export_data,
                headers={"Content-Type": "application/json"},
                timeout=40,
            )

            self.env["blogcreator.n8n.response"].create(
                {
                    "note_id": self.id,
                    "response_time": fields.Datetime.now(),
                    "status_code": response.status_code,
                    "response_content": response.text,
                }
            )

            # Kiểm tra phản hồi
            if response.status_code in (200, 201):
                # Nếu thành công, đánh dấu là đã xuất
                self.write(
                    {
                        "exported_to_n8n": True,
                        "export_date": fields.Datetime.now(),
                        "state": "exported",
                    }
                )

                self.message_post(body="Đã tạo bài viết thành công")

                return {
                    "type": "ir.actions.act_window",
                    "res_model": "blogcreator.note",
                    "res_id": self.id,
                    "view_mode": "form",
                    "target": "current",
                    "context": {"form_view_ref": "blogcreator.view_blogpost_form"},
                    "tag": "display_notification",
                    "params": {
                        "title": "Thành công",
                        "message": f'Bài viết "{self.title}" đã được tạo.',
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise Exception(
                    f"Lỗi khi gửi đến n8n: Mã phản hồi {response.status_code}, Nội dung: {response.text}"
                )

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Error in export_to_n8n: {error_msg}")
            _logger.exception("Exception details:")
            self.message_post(
                body=f"<p style='color:red'>Lỗi khi xuất sang n8n: {error_msg}</p>"
            )
            return self._show_error_notification(error_msg)

    def _show_error_notification(self, message):
        """Hiển thị thông báo lỗi"""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Lỗi",
                "message": message,
                "type": "danger",
                "sticky": True,
            },
        }

    def retry_export_to_n8n(self):
        """Thử lại việc xuất sang n8n"""
        self.ensure_one()
        self.write(
            {
                "exported_to_n8n": False,
                "export_date": False,
            }
        )
        self.update_state()
        self.message_post(body="Đã reset trạng thái xuất sang n8n để thử lại")
        return self.export_to_n8n()

    def action_approve(self):
        self.ensure_one()

        if self.state != "exported":
            raise UserError("Chỉ có thể xuất bản bài viết đã được tạo!")

        self.write({"is_published": True, "state": "approved"})

        self.message_post(body="Đã xuất bản bài viết")

        return {
            "type": "ir.actions.act_window",
            "res_model": "blogcreator.note",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_recreate_post(self):
        self.ensure_one()

        if self.state not in ["exported", "approved"]:
            raise UserError("Chỉ có thể tạo lại bài viết đã được tạo hoặc đã xuất bản!")

        self.write(
            {
                "exported_to_n8n": False,
                "export_date": False,
                "is_published": False,
                "state": "draft",
            }
        )

        self.message_post(body="Bắt đầu tạo lại bài viết...")

        return self.export_to_n8n()

    def action_unapprove(self):
        self.ensure_one()

        if self.state != "approved":
            raise UserError("Chỉ có thể hủy xuất bản bài viết đã được xuất bản!")

        self.write({"is_published": False, "state": "exported"})

        self.message_post(body="Đã hủy xuất bản bài viết")

        return {
            "type": "ir.actions.act_window",
            "res_model": "blogcreator.note",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_add_image(self):
        """Thêm hình ảnh mới bằng cách mở form với context đúng"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tải hình ảnh mới",
            "res_model": "blogcreator.image",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_note_id": self.id,
                "force_note_id": self.id,
            },
        }
