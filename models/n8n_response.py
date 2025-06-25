# models/n8n_response.py
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class N8nResponse(models.Model):
    _name = "blogcreator.n8n.response"
    _description = "N8n Webhook Response"
    _order = "create_date desc"
    _rec_name = "response_id"

    response_id = fields.Char(
        string="Mã phản hồi",
        required=True,
        copy=False,
        default=lambda self: self._get_default_response_id(),
    )
    note_id = fields.Many2one(
        "blogcreator.note", string="Bài viết", required=True, ondelete="cascade"
    )
    response_time = fields.Datetime(
        string="Thời gian nhận phản hồi", default=fields.Datetime.now
    )
    status_code = fields.Integer(string="Mã trạng thái")
    response_content = fields.Text(string="Nội dung phản hồi")
    success = fields.Boolean(
        string="Thành công", compute="_compute_success", store=True
    )

    # Thêm các trường mới
    status_description = fields.Char(
        string="Mô tả trạng thái", compute="_compute_status_description", store=True
    )
    formatted_response = fields.Html(
        string="Nội dung đã định dạng", compute="_compute_formatted_response"
    )

    def _get_default_response_id(self):
        """Tạo mã phản hồi mặc định"""
        return f"RES{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"

    @api.depends("status_code")
    def _compute_success(self):
        for record in self:
            record.success = record.status_code in (200, 201)

    @api.depends("status_code")
    def _compute_status_description(self):
        status_mapping = {
            200: "Thành công",
            201: "thành công",
            400: "Thất bại",
            401: "Thất bại",
            403: "Thất bại",
            404: "Thất bại",
            500: "Thất bại",
            503: "Thất bại",
        }

        for record in self:
            if record.status_code:
                record.status_description = status_mapping.get(
                    record.status_code, f"Mã phản hồi: {record.status_code}"
                )
            else:
                record.status_description = "Không xác định"

    @api.depends("response_content")
    def _compute_formatted_response(self):
        for record in self:
            if not record.response_content:
                record.formatted_response = False
                continue

            try:
                # Thử chuyển đổi JSON thành định dạng dễ đọc
                import json
                import markdown  # Thư viện để chuyển đổi Markdown sang HTML

                data = json.loads(record.response_content)

                # Kiểm tra xem 'final_content' có tồn tại trong response_content
                if "final_content" in data:
                    final_content = data["final_content"]

                    # Loại bỏ dòng '```markdown' và '```' khỏi nội dung
                    lines = final_content.splitlines()
                    filtered_lines = [
                        line for line in lines if not line.strip().startswith("```")
                    ]
                    cleaned_content = "\n".join(filtered_lines)

                    # Chuyển đổi Markdown đã làm sạch sang HTML
                    html_content = markdown.markdown(cleaned_content)

                    # Gán HTML đã chuyển đổi vào formatted_response
                    record.formatted_response = html_content

                    if record.note_id:
                        record.note_id.n8n_content = html_content
                else:
                    # Nếu không có 'final_content', hiển thị toàn bộ JSON như trước
                    html = "<dl class='row'>"
                    for key, value in data.items():
                        html += f"<dt class='col-sm-3'>{key}</dt>"
                        if isinstance(value, (dict, list)):
                            value_str = json.dumps(value, indent=2, ensure_ascii=False)
                            html += f"<dd class='col-sm-9'><pre>{value_str}</pre></dd>"
                        else:
                            html += f"<dd class='col-sm-9'>{value}</dd>"
                    html += "</dl>"
                    record.formatted_response = html
            except Exception as e:
                # Nếu không phải JSON hoặc có lỗi xử lý
                record.formatted_response = f"<pre>{record.response_content}</pre>"

    # def retry_export(self):
    #     """Thử lại việc xuất blog post sang n8n"""
    #     self.ensure_one()
    #     return (
    #         self.note_id.retry_export_to_n8n()
    #         if hasattr(self.note_id, "retry_export_to_n8n")
    #         else {"type": "ir.actions.act_window_close"}
    #     )
