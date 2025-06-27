# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import unicodedata


class BlogCategory(models.Model):
    _name = "blogcreator.category"
    _description = "Blog Categories Management"
    _rec_name = "name"
    _order = "name"

    name = fields.Char(
        string="Tên thể loại", required=True, help="Tên hiển thị của thể loại"
    )

    code = fields.Char(
        string="Mã thể loại", readonly=True, help="Mã tự động tạo từ tên thể loại"
    )

    prompt = fields.Text(
        string="Ngữ điệu", required=True, help="Mô tả ngữ điệu viết cho thể loại này"
    )

    def _generate_code_from_name(self, name):
        """Tự động tạo code từ name"""
        if not name:
            return False

        # Chuyển Unicode về ASCII và loại bỏ dấu
        name_ascii = unicodedata.normalize("NFD", name.lower())
        name_ascii = "".join(c for c in name_ascii if unicodedata.category(c) != "Mn")

        # Mapping các ký tự Việt Nam đặc biệt
        mapping = {"đ": "d", "ă": "a", "â": "a", "ê": "e", "ô": "o", "ơ": "o", "ư": "u"}

        for viet, eng in mapping.items():
            name_ascii = name_ascii.replace(viet, eng)

        # Chỉ giữ chữ và số, thay space bằng underscore
        code = re.sub(r"[^a-z0-9\s]", "", name_ascii)
        code = re.sub(r"\s+", "_", code.strip())

        # Giới hạn độ dài
        return code[:30] if code else "category"

    @api.model
    def create(self, vals):
        """Tự động tạo code khi tạo mới"""
        if "name" in vals:
            base_code = self._generate_code_from_name(vals["name"])

            # Đảm bảo code unique
            code = base_code
            counter = 1
            while self.search([("code", "=", code)]):
                code = f"{base_code}_{counter}"
                counter += 1

            vals["code"] = code

        return super().create(vals)

    def write(self, vals):
        """Cập nhật code khi tên thay đổi"""
        if "name" in vals:
            for record in self:
                base_code = record._generate_code_from_name(vals["name"])

                # Đảm bảo code unique (trừ chính record này)
                code = base_code
                counter = 1
                while self.search([("code", "=", code), ("id", "!=", record.id)]):
                    code = f"{base_code}_{counter}"
                    counter += 1

                vals["code"] = code

        return super().write(vals)

    @api.model
    def get_selection_list(self):
        """Trả về danh sách selection cho field note_type"""
        categories = self.search([], order="name")
        return [(cat.code, cat.name) for cat in categories]

    @api.model
    def get_prompt_dict(self):
        """Trả về dictionary mapping code -> prompt"""
        categories = self.search([])
        return {cat.code: cat.prompt for cat in categories}
