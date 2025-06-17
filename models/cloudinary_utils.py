# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
import cloudinary
import cloudinary.uploader
import cloudinary.api
import traceback
from io import BytesIO

_logger = logging.getLogger(__name__)


class CloudinaryUtils(models.AbstractModel):
    _name = "blogcreator.cloudinary.utils"
    _description = "Cloudinary Integration Utilities"

    def initialize_cloudinary(self):
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

    def upload_to_cloudinary(
        self, image_data, public_id=None, folder=None, is_thumbnail=False
    ):
        """Tải hình ảnh lên Cloudinary
        :param image_data: Dữ liệu hình ảnh (base64 string hoặc URL)
        :param public_id: ID công khai cho tài nguyên (tùy chọn)
        :param folder: Thư mục trên Cloudinary (tùy chọn)
        :return: Thông tin phản hồi từ Cloudinary
        """
        self.initialize_cloudinary()

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

            if is_thumbnail:
                upload_options.update(
                    {
                        "transformation": [
                            {
                                "width": 400,
                                "height": 300,
                                "crop": "fill",
                                "gravity": "auto",
                            },
                            {"quality": "auto:good"},
                        ]
                    }
                )

            _logger.info(f"Uploading image to Cloudinary in folder: {folder}")
            _logger.info(f"Image data type: {type(image_data)}")

            if image_data is None:
                raise ValueError("Image data is None")

            # Xử lý trường hợp đặc biệt của Odoo
            if (
                hasattr(self, "_context")
                and self._context.get("bin_size", False)
                and hasattr(image_data, "name")
            ):
                # Trường hợp đặc biệt: Odoo cung cấp kích thước thay vì dữ liệu hình ảnh
                # trong chế độ bin_size
                _logger.warning("Detected bin_size mode, trying to get full image data")
                # Tìm giải pháp khác để lấy dữ liệu hình ảnh đầy đủ
                # Đây là một điểm cải thiện trong tương lai

            # Xử lý dựa trên loại dữ liệu
            if isinstance(image_data, BytesIO):
                _logger.info("Uploading BytesIO data to Cloudinary")
                response = cloudinary.uploader.upload(image_data, **upload_options)
            elif isinstance(image_data, bytes):
                # Kiểm tra xem liệu bytes có phải là chuỗi UTF-8 không
                try:
                    decoded_str = image_data.decode("utf-8")
                    # Nếu decode thành công, đây có thể là base64 string được lưu dưới dạng bytes
                    _logger.info(
                        "Bytes data appears to be a UTF-8 string, trying as base64"
                    )
                    # Kiểm tra xem có phải base64 không
                    try:
                        # Thử phân tích như base64
                        base64.b64decode(decoded_str)
                        _logger.info("Valid base64 string detected")
                        # Sử dụng chuỗi base64 đã decode
                        response = cloudinary.uploader.upload(
                            BytesIO(base64.b64decode(decoded_str)), **upload_options
                        )
                    except Exception:
                        # Không phải base64 hợp lệ, thử cách khác
                        _logger.info("Not a valid base64 string, trying with data URL")
                        response = cloudinary.uploader.upload(
                            f"data:image/png;base64,{decoded_str}", **upload_options
                        )
                except UnicodeDecodeError:
                    # Nếu không phải chuỗi UTF-8, giả định là dữ liệu hình ảnh nhị phân
                    _logger.info("Bytes data not UTF-8, treating as binary image")
                    response = cloudinary.uploader.upload(
                        BytesIO(image_data), **upload_options
                    )
            elif isinstance(image_data, str):
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
                        _logger.info("Trying to decode as base64")
                        padding_needed = len(image_data) % 4
                        if padding_needed:
                            image_data += "=" * (4 - padding_needed)

                        # Xử lý base64 có thể có các ký tự không hợp lệ
                        image_data = image_data.replace(" ", "+")

                        image_data_binary = base64.b64decode(image_data)
                        response = cloudinary.uploader.upload(
                            BytesIO(image_data_binary), **upload_options
                        )
                    except Exception as e:
                        _logger.error(f"Invalid base64 data: {str(e)}")
                        # Thử với cách khác - thêm header data:image
                        try:
                            # Thêm header thích hợp cho dữ liệu base64
                            base64_with_header = f"data:image/png;base64,{image_data}"
                            _logger.info("Trying with data:image header")
                            response = cloudinary.uploader.upload(
                                base64_with_header, **upload_options
                            )
                        except Exception as e:
                            _logger.error(
                                f"Still failed with data:image header: {str(e)}"
                            )
                            # Cuối cùng, thử xem liệu đây có phải là đường dẫn file không
                            try:
                                import os

                                if os.path.exists(image_data):
                                    _logger.info(
                                        f"Trying to upload file from path: {image_data}"
                                    )
                                    response = cloudinary.uploader.upload(
                                        image_data, **upload_options
                                    )
                                else:
                                    raise ValueError(
                                        f"Path doesn't exist: {image_data}"
                                    )
                            except Exception:
                                _logger.error("All attempts failed")
                                raise
            else:
                # Đối tượng file-like
                _logger.info(f"Uploading object to Cloudinary: {type(image_data)}")
                response = cloudinary.uploader.upload(image_data, **upload_options)

            _logger.info(
                f"Image uploaded successfully to Cloudinary: {response.get('secure_url')}"
            )
            return response

        except Exception as e:
            _logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
            _logger.exception("Exception details:")

            # Thử một lần cuối với cách khác - lấy dữ liệu thô từ attachment nếu có thể
            try:
                _logger.info("Last resort: trying to get attachment data directly")
                # Đây là phương pháp dự phòng cuối cùng - nếu model có liên quan đến image_ids
                # Đây không phải là phần tốt nhất, nhưng chỉ là một backup
                model_name = self._name
                record_id = self.id

                attachment = self.env["ir.attachment"].search(
                    [
                        ("res_model", "=", model_name),
                        ("res_id", "=", record_id),
                    ],
                    limit=1,
                )

                if attachment:
                    attachment_data = attachment.with_context(bin_size=False).datas
                    if attachment_data:
                        _logger.info("Found attachment data, trying to upload")
                        binary_data = base64.b64decode(attachment_data)
                        result = cloudinary.uploader.upload(
                            BytesIO(binary_data), **upload_options
                        )
                        return result
            except Exception as rescue_error:
                _logger.error(f"Last resort attempt also failed: {str(rescue_error)}")

            raise UserError(_("Failed to upload image to Cloudinary: %s") % str(e))
