# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import base64
from bs4 import BeautifulSoup
import cloudinary
import cloudinary.uploader
import cloudinary.api
import re
import traceback
import sys
from io import BytesIO

_logger = logging.getLogger(__name__)


class BlogNote(models.Model):
    _name = "blogcreator.note"
    _description = "Blog Notes for n8n Integration"
    _rec_name = "title"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # Thêm tính năng chatter

    title = fields.Char(string="Tiêu đề", required=True, tracking=True)
    content = fields.Html(
        string="Nội dung", tracking=True
    )  # Đổi từ Text sang Html để hỗ trợ định dạng
    note_type = fields.Selection(
        [
            ("general", "Thông tin chung"),
            ("tech", "Công nghệ"),
            ("business", "Kinh doanh"),
            ("sport", "Thể thao"),
            ("health", "Sức khỏe"),
            ("entertainment", "Giải trí"),
            ("other", "Khác"),
        ],
        string="Loại ghi chú",
        default="general",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("published", "Đã xuất bản"),
            ("exported", "Đã xuất sang n8n"),
        ],
        string="Trạng thái",
        default="draft",
        tracking=True,
    )
    is_published = fields.Boolean(string="Đã xuất bản", default=False, tracking=True)
    exported_to_n8n = fields.Boolean(
        string="Đã xuất sang n8n", default=False, tracking=True
    )
    export_date = fields.Datetime(string="Ngày xuất", readonly=True)
    tags = fields.Char(
        string="Tags", help="Các tag cách nhau bởi dấu phẩy", tracking=True
    )
    # Thêm trường user để biết ai tạo note
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
    image_name = fields.Char(string="Tên file hình ảnh")
    # Thêm trường cho nhiều hình ảnh (sử dụng Many2many)
    image_ids = fields.One2many("blogcreator.image", "note_id", string="Hình ảnh")

    def _initialize_cloudinary(self):
        """Khởi tạo cấu hình Cloudinary từ System Parameters"""
        cloud_name = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("blogcreator.cloudinary_cloud_name")
        )
        api_key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("blogcreator.cloudinary_api_key")
        )
        api_secret = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("blogcreator.cloudinary_api_secret")
        )

        missing_params = []
        if not cloud_name:
            missing_params.append("Cloud Name")
        if not api_key:
            missing_params.append("API Key")
        if not api_secret:
            missing_params.append("API Secret")

        if missing_params:
            raise UserError(
                _(
                    "Cloudinary configuration is incomplete. The following parameters are missing: %s. "
                    "Please set these parameters in System Parameters (Settings > Technical > Parameters > System Parameters)."
                )
                % ", ".join(missing_params)
            )

        # Khởi tạo Cloudinary
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
        return True

    def upload_to_cloudinary(self, image_data, public_id=None, folder=None):
        """Tải hình ảnh lên Cloudinary

        :param image_data: Dữ liệu hình ảnh (base64 string hoặc URL)
        :param public_id: ID công khai cho tài nguyên (tùy chọn)
        :param folder: Thư mục trên Cloudinary (tùy chọn)
        :return: Thông tin phản hồi từ Cloudinary
        """
        self._initialize_cloudinary()

        # Lấy thư mục mặc định nếu không có
        if not folder:
            folder = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("blogcreator.cloudinary_upload_folder", "blogcreator")
            )

        try:
            # Chuẩn bị tùy chọn tải lên
            upload_options = {"folder": folder, "tags": ["blog", "blogcreator"]}

            if public_id:
                upload_options["public_id"] = public_id

            _logger.info(f"Uploading image to Cloudinary in folder: {folder}")
            _logger.info(f"Image data type: {type(image_data)}")

            # Xác định loại dữ liệu hình ảnh và tải lên
            if isinstance(image_data, str):
                if image_data.startswith("data:image"):
                    # Dữ liệu URL data
                    _logger.info("Uploading data URL to Cloudinary")
                    response = cloudinary.uploader.upload(image_data, **upload_options)
                elif image_data.startswith(("http://", "https://")):
                    # URL hình ảnh
                    _logger.info(f"Uploading image URL to Cloudinary: {image_data}")
                    response = cloudinary.uploader.upload(image_data, **upload_options)
                else:
                    # Chuỗi Base64
                    _logger.info("Uploading base64 data to Cloudinary")
                    try:
                        # Thử giải mã base64 để xem nó có hợp lệ không
                        image_data_binary = base64.b64decode(image_data)
                        _logger.info("Base64 data is valid")
                        response = cloudinary.uploader.upload(
                            BytesIO(image_data_binary), **upload_options
                        )
                    except Exception as e:
                        _logger.error(f"Invalid base64 data: {str(e)}")
                        # Thử tải lên với định dạng data URL
                        response = cloudinary.uploader.upload(
                            f"data:image/png;base64,{image_data}", **upload_options
                        )
            else:
                # Dữ liệu nhị phân
                _logger.info("Uploading binary data to Cloudinary")
                response = cloudinary.uploader.upload(
                    BytesIO(image_data), **upload_options
                )

            _logger.info(
                f"Image uploaded successfully to Cloudinary: {response.get('secure_url')}"
            )
            return response

        except Exception as e:
            _logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
            _logger.exception("Exception details:")
            raise UserError(_("Failed to upload image to Cloudinary: %s") % str(e))

    @api.model
    def write(self, vals):
        """Ghi đè hàm write để cập nhật state khi thay đổi trạng thái xuất bản"""
        res = super(BlogNote, self).write(vals)
        # Cập nhật state dựa trên các trạng thái
        if "is_published" in vals or "exported_to_n8n" in vals:
            for record in self:
                if record.exported_to_n8n:
                    record.state = "exported"
                elif record.is_published:
                    record.state = "published"
                else:
                    record.state = "draft"
        return res

    def mark_as_exported(self):
        """Đánh dấu note đã được xuất sang n8n"""
        for record in self:
            record.write(
                {
                    "exported_to_n8n": True,
                    "export_date": fields.Datetime.now(),
                    "state": "exported",
                }
            )
            # Thêm tin nhắn vào chatter
            record.message_post(body="Đã xuất thành công sang n8n")
        return True

    def export_to_n8n(self):
        """Hàm chuẩn bị và xuất dữ liệu sang n8n"""
        self.ensure_one()
        try:
            # Khởi tạo biến debug_exceptions
            debug_exceptions = []

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
                    blog_title_slug = re.sub(r"[^a-zA-Z0-9_]", "_", self.title.lower())
                    public_id = f"blog_{self.id}_{blog_title_slug}_main"

                    # Upload lên Cloudinary
                    response = self.upload_to_cloudinary(
                        image_data,
                        public_id=public_id,
                        folder="blog_creator/main_images",
                    )

                    if response and response.get("secure_url"):
                        main_cloudinary_image = response["secure_url"]
                        _logger.info(
                            f"Main image uploaded to Cloudinary: {main_cloudinary_image}"
                        )

                        # Thêm hình ảnh chính vào danh sách hình ảnh để xử lý
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

                try:
                    soup = BeautifulSoup(html_content, "html.parser")
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
                            response = self.upload_to_cloudinary(
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
                            # Thêm vào debug_exceptions
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
                    updated_html = str(new_soup)
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
                    updated_html = html_content
            else:
                updated_html = html_content
                _logger.info("No HTML content to process")

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
                    }
                    image_ids_details.append(record_info)

                    if hasattr(img_record, "image") and img_record.image:
                        try:
                            _logger.info(f"Processing gallery image {idx+1}")
                            _logger.info(f"Image type: {type(img_record.image)}")
                            # Chuyển đổi dữ liệu hình ảnh sang định dạng phù hợp
                            image_data = img_record.image
                            if not isinstance(image_data, str):
                                # Nếu image_data là bytes, chuyển đổi sang base64 string
                                image_data = (
                                    base64.b64encode(image_data).decode("utf-8")
                                    if isinstance(image_data, bytes)
                                    else image_data
                                )

                            # Tải lên Cloudinary
                            image_public_id = f"blog_{self.id}_gallery_image_{idx+1}"
                            response = self.upload_to_cloudinary(
                                image_data,
                                public_id=image_public_id,
                                folder="blog_creator/gallery_images",
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
                                    "width": response.get("width"),
                                    "height": response.get("height"),
                                    "is_gallery": True,
                                }
                            )
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

            # Chuẩn bị dữ liệu để xuất
            export_data = {
                "id": self.id,
                "title": self.title,
                "content": self.content,
                "cloudinary_content": updated_html,
                "note_type": dict(self._fields["note_type"].selection).get(
                    self.note_type
                ),
                "tags": self.tags,
                "is_published": self.is_published,
                "create_date": fields.Datetime.to_string(self.create_date),
                "user": self.env.user.name,
                "main_image": main_cloudinary_image,
                "content_images": cloudinary_images,
                # Thêm debug info
                "debug_info": {
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
                        "has_api_secret": bool(
                            self.env["ir.config_parameter"]
                            .sudo()
                            .get_param("blogcreator.cloudinary_api_secret")
                        ),
                        "upload_folder": self.env["ir.config_parameter"]
                        .sudo()
                        .get_param("blogcreator.cloudinary_upload_folder", "Not set"),
                    },
                    "exceptions": debug_exceptions,
                    "image_ids_details": image_ids_details,
                },
            }

            _logger.info(f"Sending data to n8n webhook: {webhook_url}")
            _logger.info(f"Number of Cloudinary images: {len(cloudinary_images)}")

            # Gửi dữ liệu tới n8n qua webhook
            response = requests.post(
                webhook_url,
                json=export_data,
                headers={"Content-Type": "application/json"},
                timeout=30,  # Tăng timeout vì có xử lý nhiều hình ảnh
            )

            # Kiểm tra phản hồi
            if response.status_code in (200, 201):
                # Nếu thành công, đánh dấu là đã xuất
                self.mark_as_exported()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Thành công",
                        "message": f'Đã xuất "{self.title}" sang n8n thành công với {len(cloudinary_images)} hình ảnh',
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

    def action_publish(self):
        """Đánh dấu bài viết là đã xuất bản"""
        for record in self:
            record.write({"is_published": True, "state": "published"})
        return True

    def action_unpublish(self):
        """Hủy xuất bản bài viết"""
        for record in self:
            record.write({"is_published": False, "state": "draft"})
        return True

    def action_reset_export(self):
        """Reset trạng thái xuất sang n8n (để có thể xuất lại)"""
        for record in self:
            record.write(
                {
                    "exported_to_n8n": False,
                    "export_date": False,
                    "state": "published" if record.is_published else "draft",
                }
            )
            record.message_post(body="Đã reset trạng thái xuất sang n8n")
        return True
