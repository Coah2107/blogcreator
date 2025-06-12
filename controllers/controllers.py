from odoo import http
from odoo.http import request
import json


class BlogNoteController(http.Controller):

    @http.route(
        "/api/blog_notes", type="http", auth="api_key", methods=["GET"], csrf=False
    )
    def get_notes(self, **kw):
        """Lấy danh sách các ghi chú chưa xuất sang n8n"""
        domain = [("exported_to_n8n", "=", False)]

        # Nếu có tham số loại note
        if kw.get("note_type"):
            domain.append(("note_type", "=", kw.get("note_type")))

        notes = request.env["blogcreator.note"].sudo().search(domain)
        result = []

        for note in notes:
            result.append(
                {
                    "id": note.id,
                    "title": note.title,
                    "content": note.content,
                    "note_type": note.note_type,
                    "tags": note.tags,
                    "create_date": (
                        note.create_date.isoformat() if note.create_date else False
                    ),
                    "user": note.user_id.name,
                }
            )

        return json.dumps(result)

    @http.route(
        "/api/blog_notes/<int:note_id>/mark_exported",
        type="http",
        auth="api_key",
        methods=["POST"],
        csrf=False,
    )
    def mark_exported(self, note_id, **kw):
        """Đánh dấu ghi chú đã được xuất sang n8n"""
        note = request.env["blogcreator.note"].sudo().browse(note_id)
        if note.exists():
            note.mark_as_exported()
            return json.dumps({"success": True})
        return json.dumps({"success": False, "error": "Note not found"})
