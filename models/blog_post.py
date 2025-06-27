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
    _inherit = ["mail.thread", "mail.activity.mixin"]

    title = fields.Char(string="Tiêu đề", required=True, tracking=True)
    content = fields.Html(string="Nội dung", tracking=True)
    note_type = fields.Selection(
        string="Thể Loại",
        selection="_get_note_type_selection",
        default="general",
        required=True,
        tracking=True,
    )
    note_type_prompt = fields.Text(
        string="Ngữ điệu",
        compute="_compute_note_type_prompt",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Soạn thảo"),
            ("submitted", "Đã gửi"),
            ("approved", "Đã duyệt"),
            ("published", "Đã đăng"),
            ("rejected", "Bị từ chối"),
            ("cancelled", "Đã hủy"),
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
    n8n_content = fields.Html(
        string="Nội dung từ n8n",
        help="Nội dung mới nhất được trả về từ n8n",
        tracking=True,
    )

    @api.model
    def _get_note_type_selection(self):
        """Lấy danh sách thể loại từ blogcreator.category"""
        try:
            categories = self.env["blogcreator.category"].get_selection_list()
            if categories:
                return [("general", "Chọn Thể Loại")] + categories
            else:
                # Fallback về hardcoded list nếu chưa có categories
                return (
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
                )
        except Exception:
            return [("general", "Chọn Thể Loại")]

    # @api.depends("note_type")
    # def _compute_note_type_prompt(self):
    #     prompts = {
    #         "general": "Vui lòng chọn thể loại phù hợp cho bài viết.",
    #         "culinary": 'Hãy viết với phong cách kích thích giác quan, tập trung mô tả hương vị, màu sắc và mùi thơm. Sử dụng giọng điệu tỉ mỉ và hào hứng.\nGợi ý động từ: "nếm", "nhấm nháp", "thưởng thức"\nGợi ý cụm từ: "hương vị nồng nàn", "vị đậm đà", "tan chảy trong miệng"',
    #         "entertainment": 'Hãy viết với phong cách sôi nổi, năng lượng cao, gợi tả không khí náo nhiệt, từ "nhạc sống" đến "gameshow"; phù hợp ban ngày lẫn cuộc sống về đêm.\nGợi ý cụm từ: "sôi động", "náo nhiệt", "party mood", "bùng nổ cảm xúc"',
    #         "wellness_healing": 'Hãy viết với phong cách nhẹ nhàng, thư thái; ngôn ngữ hướng đến trải nghiệm cân bằng và chữa lành; nhịp câu chậm, có thể sử dụng dấu ba chấm để tạo cảm giác thả lỏng.\nGợi ý cụm từ: "thư giãn sâu", "hồi phục năng lượng", "cân bằng tâm trí"',
    #         "adventure": 'Hãy viết với phong cách hứng khởi, kịch tính; sử dụng từ ngữ mạnh mẽ gợi cảm giác chinh phục; phù hợp leo núi, trekking, mạo hiểm ngoài trời.\nGợi ý cụm từ: "chinh phục đỉnh cao", "thót tim", "bứt phá", "khám phá vùng đất mới"',
    #         "family_friendly": 'Hãy viết với phong cách ấm áp, an toàn; tạo cảm giác thoải mái cho mọi lứa tuổi; nhấn mạnh tiện nghi và không gian rộng rãi để gia đình cùng trải nghiệm.\nGợi ý cụm từ: "phù hợp trẻ em", "an toàn tuyệt đối", "không gian sum họp"',
    #         "insta_worthy": 'Hãy viết với phong cách trẻ trung, trend-hungry; dùng hashtag và emoji; ngôn từ khơi gợi cảm hứng sống ảo, chú trọng background và ánh sáng.\nGợi ý cụm từ: "#travelgoals", "background triệu like", "góc sống ảo", "check-in hot nhất"',
    #         "eco_friendly": 'Hãy viết với phong cách thân thiện môi trường; ngôn ngữ thể hiện trách nhiệm xã hội, kêu gọi bảo tồn; dùng từ "zero-waste", "sinh thái", "bảo tồn".\nGợi ý cụm từ: "hạn chế rác thải", "hòa mình thiên nhiên", "phát triển bền vững"',
    #         "coworking_remote": 'Hãy viết với phong cách chuyên nghiệp, thực dụng; tập trung vào hiệu quả làm việc: "wifi mạnh", "ổ cắm đủ", "không gian yên tĩnh"; phù hợp freelance & remote.\nGợi ý cụm từ: "wifi 500Mbps", "quiet zone", "không gian làm việc lý tưởng"',
    #         "shopping_spree": 'Hãy viết với phong cách hào hứng, khơi gợi thú săn lùng ưu đãi; ngôn từ thể hiện xu hướng thời trang, sale hấp dẫn và trải nghiệm mua sắm năng động.\nGợi ý cụm từ: "sale off", "must-have item", "săn deal hot", "giảm giá sốc"',
    #         "arts_exhibition": 'Hãy viết với phong cách trí thức, sâu sắc; ngôn từ mỹ thuật, nhấn mạnh chi tiết tác phẩm, ý tưởng & cảm nhận nghệ thuật.\nGợi ý cụm từ: "chất liệu sơn dầu", "installation art", "composition tinh tế", "triển lãm độc đáo"',
    #         "spa_relaxation": 'Hãy viết với phong cách nhẹ nhàng, thanh bình; ngôn ngữ miêu tả thư giãn sâu sắc, chăm sóc cơ thể & tinh thần.\nGợi ý cụm từ: "tinh dầu lavender", "massaging flow", "xông hơi đá muối", "liệu pháp thư giãn"',
    #         "street_food": 'Hãy viết với phong cách sinh động, chân thật; tái hiện mùi vị, âm thanh & không gian đặc trưng của hàng rong, xiên nướng, cháo lòng…\nGợi ý cụm từ: "xiên nướng thơm lừng", "tiếng xèo xèo", "hương vị đường phố", "quán vỉa hè"',
    #         "hidden_gems": 'Hãy viết với phong cách bí ẩn, khơi gợi tò mò; mô tả yếu tố bất ngờ, hoang sơ, ít người biết đến.\nGợi ý cụm từ: "ẩn mình", "chưa lên bản đồ", "hoang sơ tuyệt đối", "địa điểm bí mật"',
    #         "photography_spot": 'Hãy viết với phong cách chuyên môn nhiếp ảnh; ngôn ngữ tập trung vào ánh sáng, góc chụp, cảm hứng sáng tạo và kỹ thuật.\nGợi ý cụm từ: "golden hour", "depth of field", "wide-angle shot", "góc chụp đẹp nhất"',
    #     }

    #     for record in self:
    #         record.note_type_prompt = prompts.get(record.note_type, "")

    @api.depends("note_type")
    def _compute_note_type_prompt(self):
        """Lấy prompt từ blogcreator.category"""
        try:
            prompt_dict = self.env["blogcreator.category"].get_prompt_dict()
            for record in self:
                record.note_type_prompt = prompt_dict.get(
                    record.note_type, "Vui lòng chọn thể loại phù hợp cho bài viết."
                )
        except Exception:
            # Fallback về hardcoded prompts
            for record in self:
                record.note_type_prompt = "Vui lòng chọn thể loại phù hợp cho bài viết."

    @api.depends("n8n_response_ids")
    def _compute_last_response(self):
        for record in self:
            record.last_n8n_response_id = self.env["blogcreator.n8n.response"].search(
                [("note_id", "=", record.id)], order="response_time desc", limit=1
            )

    def _get_thumbnail_url(self):
        """
        Tìm URL thumbnail từ nội dung HTML
        """
        if not self.content:
            return None

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(self.content, "html.parser")
            img_tags = soup.find_all("img")

            if img_tags and len(img_tags) > 0:
                # Lấy URL của hình ảnh đầu tiên
                first_img = img_tags[0]
                return first_img.get("src")
        except Exception as e:
            _logger.error(f"Error getting thumbnail URL: {str(e)}")

        return None

    def create_ai_content(self):
        """Tạo nội dung AI và hiển thị trong tab 'Nội dung' mà không thay đổi trạng thái"""
        self.ensure_one()

        try:
            # Khởi tạo biến
            debug_exceptions = []
            cloudinary_images = []
            thumbnail_url = None
            cloudinary_utils = self.env["blogcreator.cloudinary.utils"]

            # Lấy URL webhook từ system parameters
            webhook_url = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("blogcreator.n8n_webhook_url")
            )

            if not webhook_url:
                raise Exception("URL webhook n8n chưa được cấu hình.")

            # Xử lý HTML content
            html_content = self.content or ""

            if html_content:
                try:
                    soup = BeautifulSoup(html_content, "html.parser")

                    # Xử lý hình ảnh trong HTML
                    img_tags = soup.find_all("img")
                    _logger.info(f"Found {len(img_tags)} img tags in HTML content")

                    # Tạo bản sao soup để xử lý text với markers
                    text_soup = BeautifulSoup(str(soup), "html.parser")
                    text_img_tags = text_soup.find_all("img")

                    # Xử lý từng hình ảnh
                    for i, img_tag in enumerate(img_tags):
                        src = img_tag.get("src", "")
                        if not src:
                            continue

                        # Tạo key từ alt hoặc image number
                        img_key = f"Image {i+1}"
                        desc_text = img_tag.get("alt", "")

                        try:
                            # Upload hình ảnh lên Cloudinary
                            image_public_id = f"blog_{self.id}_content_image_{i+1}"
                            response = cloudinary_utils.upload_to_cloudinary(
                                src,
                                public_id=image_public_id,
                                folder="blog_creator/content_images",
                                is_thumbnail=(i == 0),
                            )

                            cloudinary_url = response.get("secure_url")

                            if i == 0 and cloudinary_url:
                                thumbnail_url = cloudinary_url
                            else:
                                # Thêm vào danh sách hình ảnh
                                cloudinary_images.append(
                                    {
                                        "url": cloudinary_url,
                                        "key": img_key,
                                        "id": i + 1,
                                        "desc": desc_text,
                                    }
                                )

                            # Thay thế hình ảnh trong text_soup với marker
                            marker = text_soup.new_string(f"({img_key})")
                            text_img_tags[i].replace_with(marker)

                        except Exception as e:
                            _logger.error(f"Error processing image {i+1}: {str(e)}")
                            debug_exceptions.append(
                                {"location": f"content_image_{i+1}", "error": str(e)}
                            )

                    # Trích xuất văn bản với markers
                    paragraphs = []
                    for elem in text_soup.find_all(
                        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div"]
                    ):
                        text = elem.get_text(strip=True)
                        if text:
                            paragraphs.append(text)

                    # Kết hợp thành văn bản hoàn chỉnh
                    plain_text_with_markers = "\n\n".join(paragraphs)

                    # Nếu không tìm thấy paragraphs, lấy toàn bộ text
                    if not plain_text_with_markers:
                        plain_text_with_markers = text_soup.get_text(
                            separator="\n\n", strip=True
                        )

                except Exception as e:
                    _logger.error(f"Error processing HTML content: {str(e)}")
                    plain_text_with_markers = ""
                    debug_exceptions.append(
                        {"location": "html_content", "error": str(e)}
                    )
            else:
                plain_text_with_markers = ""

            # Chuẩn bị dữ liệu để xuất
            export_data = {
                "id": self.id,
                "title": self.title,
                "content": plain_text_with_markers,
                "note_type_prompt": self.note_type_prompt,
                "tags": self.tags,
                "create_date": fields.Datetime.to_string(self.create_date),
                "user": self.env.user.name,
                "thumbnail": thumbnail_url,
                "content_images": cloudinary_images,
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
                    "has_img_tags": len(img_tags) if "img_tags" in locals() else 0,
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
                try:
                    import json

                    response_data = json.loads(response.text)
                    if "final_content" in response_data:
                        final_content = response_data["final_content"]
                        formatted_html = self._format_ai_content(
                            final_content, cloudinary_images
                        )
                        self.write({"n8n_content": formatted_html})
                        _logger.info("Đã lưu nội dung từ response n8n")
                except Exception as e:
                    _logger.error(f"Lỗi khi xử lý nội dung từ n8n: {str(e)}")
                    return self._show_error_notification(str(e))

                self.message_post(body="Đã tạo nội dung thành công")

                return {
                    "type": "ir.actions.act_window",
                    "res_model": "blogcreator.note",
                    "res_id": self.id,
                    "view_mode": "form",
                    "target": "current",
                    "context": {
                        "form_view_initial_mode": "edit",
                        "force_activate_tab": "nội_dung",
                    },
                    "flags": {
                        "mode": "edit",
                        "initial_mode": "edit",
                    },
                    "tag": "display_notification",
                    "params": {
                        "title": "Thành công",
                        "message": "Nội dung AI đã được tạo và hiển thị trong tab Nội dung.",
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
            _logger.error(f"Error in create_ai_content: {error_msg}")
            _logger.exception("Exception details:")
            self.message_post(
                body=f"<p style='color:red'>Lỗi khi tạo nội dung AI: {error_msg}</p>"
            )
            return self._show_error_notification(error_msg)

    def _format_ai_content(self, content, cloudinary_images=None):
        """Định dạng nội dung AI và chỉ thêm các class CSS"""
        try:
            import markdown

            # Loại bỏ dòng ```markdown và ``` từ nội dung
            lines = content.splitlines()
            filtered_lines = [
                line for line in lines if not line.strip().startswith("```")
            ]
            cleaned_content = "\n".join(filtered_lines)

            # Chuyển đổi Markdown thành HTML với một số extension
            html_content = markdown.markdown(
                cleaned_content, extensions=["extra", "nl2br", "tables", "sane_lists"]
            )

            # Thay thế placeholder hình ảnh nếu có
            if cloudinary_images:
                for img in cloudinary_images:
                    img_key = img.get("key", "")
                    img_url = img.get("url", "")
                    if img_key and img_url:
                        img_placeholder = f"({img_key})"
                        img_html = f'<figure class="ai-figure">'
                        img_html += (
                            f'<img src="{img_url}" alt="{img_key}" class="ai-image">'
                        )
                        img_html += (
                            f'<figcaption class="ai-caption">{img_key}</figcaption>'
                        )
                        img_html += "</figure>"
                        html_content = html_content.replace(img_placeholder, img_html)

            # Bọc trong div với class ai-content
            formatted_html = f'<div class="ai-content">{html_content}</div>'

            return formatted_html
        except Exception as e:
            _logger.error(f"Lỗi khi định dạng nội dung AI: {str(e)}")
            return f"<div class='alert alert-warning'>Không thể định dạng nội dung: {str(e)}</div>{content}"

    def submit_blog_post(self):
        """Nộp bài viết để xét duyệt"""
        self.ensure_one()

        if self.state != "draft":
            raise UserError(_("Chỉ có thể nộp bài viết ở trạng thái nháp!"))

        if not self.title or not self.content:
            raise UserError(
                _("Vui lòng điền đầy đủ tiêu đề và nội dung trước khi nộp bài!")
            )

        self.write(
            {
                "state": "submitted",
                "exported_to_n8n": False,  # Không đánh dấu là đã xuất sang n8n
            }
        )

        self.message_post(body="Đã nộp bài viết để xét duyệt")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Bài viết đã được nộp để xét duyệt.",
                "type": "success",
                "sticky": False,
            },
        }

    def export_to_n8n(self):
        """Hàm chuẩn bị và xuất dữ liệu sang n8n"""
        self.ensure_one()

        if self.state != "draft":
            raise UserError("Chỉ có thể tạo bài viết từ trạng thái nháp!")

        try:
            # Khởi tạo biến
            debug_exceptions = []
            cloudinary_images = []
            thumbnail_url = None
            cloudinary_utils = self.env["blogcreator.cloudinary.utils"]

            # Lấy URL webhook từ system parameters
            webhook_url = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("blogcreator.n8n_webhook_url")
            )

            if not webhook_url:
                raise Exception("URL webhook n8n chưa được cấu hình.")

            # Xử lý HTML content
            html_content = self.content or ""

            if html_content:
                try:
                    soup = BeautifulSoup(html_content, "html.parser")

                    # Xử lý hình ảnh trong HTML
                    img_tags = soup.find_all("img")
                    _logger.info(f"Found {len(img_tags)} img tags in HTML content")

                    # Tạo bản sao soup để xử lý text với markers
                    text_soup = BeautifulSoup(str(soup), "html.parser")
                    text_img_tags = text_soup.find_all("img")

                    # Xử lý từng hình ảnh
                    for i, img_tag in enumerate(img_tags):
                        src = img_tag.get("src", "")
                        if not src:
                            continue

                        # Tạo key từ alt hoặc image number
                        img_key = f"Image {i+1}"

                        try:
                            # Upload hình ảnh lên Cloudinary
                            image_public_id = f"blog_{self.id}_content_image_{i+1}"
                            response = cloudinary_utils.upload_to_cloudinary(
                                src,
                                public_id=image_public_id,
                                folder="blog_creator/content_images",
                                is_thumbnail=(i == 0),
                            )

                            # Lấy URL từ Cloudinary
                            cloudinary_url = response.get("secure_url")

                            # Lưu thumbnail URL (hình đầu tiên)
                            if i == 0 and cloudinary_url:
                                thumbnail_url = cloudinary_url

                            # Thêm vào danh sách hình ảnh
                            cloudinary_images.append(
                                {"url": cloudinary_url, "key": img_key, "id": i + 1}
                            )

                            # Thay thế hình ảnh trong text_soup với marker
                            marker = text_soup.new_string(f"({img_key})")
                            text_img_tags[i].replace_with(marker)

                        except Exception as e:
                            _logger.error(f"Error processing image {i+1}: {str(e)}")
                            debug_exceptions.append(
                                {"location": f"content_image_{i+1}", "error": str(e)}
                            )

                    # Trích xuất văn bản với markers
                    paragraphs = []
                    for elem in text_soup.find_all(
                        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div"]
                    ):
                        text = elem.get_text(strip=True)
                        if text:
                            paragraphs.append(text)

                    # Kết hợp thành văn bản hoàn chỉnh
                    plain_text_with_markers = "\n\n".join(paragraphs)

                    # Nếu không tìm thấy paragraphs, lấy toàn bộ text
                    if not plain_text_with_markers:
                        plain_text_with_markers = text_soup.get_text(
                            separator="\n\n", strip=True
                        )

                except Exception as e:
                    _logger.error(f"Error processing HTML content: {str(e)}")
                    plain_text_with_markers = ""
                    debug_exceptions.append(
                        {"location": "html_content", "error": str(e)}
                    )
            else:
                plain_text_with_markers = ""

            # Chuẩn bị dữ liệu để xuất
            export_data = {
                "id": self.id,
                "title": self.title,
                "content": plain_text_with_markers,
                "note_type": dict(self._fields["note_type"].selection).get(
                    self.note_type
                ),
                "tags": self.tags,
                "is_published": self.is_published,
                "create_date": fields.Datetime.to_string(self.create_date),
                "user": self.env.user.name,
                "thumbnail": thumbnail_url,
                "content_images": cloudinary_images,
            }

            # Thêm debug info nếu cần
            include_debug = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("blogcreator.include_debug_info", "False")
                .lower()
                == "true"
            )

            if include_debug:
                export_data["debug_info"] = {
                    "has_main_image": bool(self.image),
                    "main_image_type": str(type(self.image)) if self.image else None,
                    "has_img_tags": len(img_tags) if "img_tags" in locals() else 0,
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

                try:
                    import json

                    response_data = json.loads(response.text)
                    if "final_content" in response_data:
                        # Lưu nội dung AI vào trường n8n_content
                        self.n8n_content = response_data["final_content"]
                        _logger.info(f"Đã lưu nội dung từ response n8n")
                except Exception as e:
                    _logger.error(f"Lỗi khi xử lý nội dung từ n8n: {str(e)}")

                self.write(
                    {
                        "exported_to_n8n": True,
                        "export_date": fields.Datetime.now(),
                        "state": "submitted",
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

    # def retry_export_to_n8n(self):
    #     """Thử lại việc xuất sang n8n"""
    #     self.ensure_one()
    #     self.write(
    #         {
    #             "exported_to_n8n": False,
    #             "export_date": False,
    #         }
    #     )
    #     self.update_state()
    #     self.message_post(body="Đã reset trạng thái xuất sang n8n để thử lại")
    #     return self.export_to_n8n()

    def action_approve(self):
        self.ensure_one()

        if not self.env.user.has_group("blogcreator.group_blogcreator_manager"):
            raise UserError(_("Chỉ giáo viên mới có quyền duyệt bài viết!"))

        if self.state != "submitted":
            raise UserError("Chỉ có thể duyệt bài viết đã được gửi!")

        self.write(
            {
                "state": "approved",
                "is_published": False,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "blogcreator.note",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_publish(self):
        self.ensure_one()

        if not self.env.user.has_group("blogcreator.group_blogcreator_manager"):
            raise UserError(_("Chỉ giáo viên mới có quyền đăng bài viết!"))

        if self.state != "approved":
            raise UserError("Chỉ có thể đăng bài viết đã được duyệt!")

        self.write(
            {
                "state": "published",
                "is_published": True,
            }
        )

        self.message_post(body="Đã đăng bài viết")

        return {
            "type": "ir.actions.act_window",
            "res_model": "blogcreator.note",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_reject(self):
        self.ensure_one()

        if not self.env.user.has_group("blogcreator.group_blogcreator_manager"):
            raise UserError(_("Chỉ giáo viên mới có quyền từ chối bài viết!"))

        if self.state != "submitted":
            raise UserError("Chỉ có thể từ chối bài viết đã được gửi!")

        self.write(
            {
                "state": "rejected",
                "is_published": False,
            }
        )

        self.message_post(
            body="Bài viết bị từ chối. Vui lòng xem xét và chỉnh sửa lại."
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "blogcreator.note",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_cancel(self):
        self.ensure_one()

        # Kiểm tra quyền - chỉ admin và người có quyền quản lý mới được hủy bài khi đã đăng/duyệt
        if self.state in ["approved", "published"] and not self.env.user.has_group(
            "blogcreator.group_blogcreator_manager"
        ):
            raise UserError(
                _("Chỉ giáo viên mới có quyền hủy bài viết đã duyệt hoặc đã đăng!")
            )

        # Người tạo và quản lý đều có thể hủy ở trạng thái soạn thảo, gửi, từ chối
        # Chỉ quản lý mới có thể hủy ở trạng thái đã duyệt, đã đăng
        if self.state == "cancelled":
            raise UserError("Bài viết đã ở trạng thái hủy!")

        # Ghi log tùy theo trạng thái trước khi hủy
        message = "Bài viết đã bị hủy"
        if self.state == "published":
            message = "Bài viết đã bị hủy (trước đó ở trạng thái đã đăng)"
        elif self.state == "approved":
            message = "Bài viết đã bị hủy (trước đó ở trạng thái đã duyệt)"

        self.write(
            {
                "state": "cancelled",
                "is_published": False,
            }
        )

        self.message_post(body=message)

        return {
            "type": "ir.actions.act_window",
            "res_model": "blogcreator.note",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_recreate_post(self):
        self.ensure_one()

        if self.state not in ["submitted", "approved"]:
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

        if not self.env.user.has_group("blogcreator.group_blogcreator_manager"):
            raise UserError(_("Chỉ giáo viên mới có quyền hủy duyệt bài viết!"))

        if self.state != "approved":
            raise UserError("Chỉ có thể hủy xuất bản bài viết đã được xuất bản!")

        self.write({"is_published": False, "state": "submitted"})

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
