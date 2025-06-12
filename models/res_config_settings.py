# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging
import cloudinary
import cloudinary.api

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cloudinary_cloud_name = fields.Char(
        string="Cloudinary Cloud Name",
        config_parameter="blogcreator.cloudinary_cloud_name",
    )
    cloudinary_api_key = fields.Char(
        string="Cloudinary API Key", config_parameter="blogcreator.cloudinary_api_key"
    )
    cloudinary_api_secret = fields.Char(
        string="Cloudinary API Secret",
        config_parameter="blogcreator.cloudinary_api_secret",
    )
    cloudinary_upload_folder = fields.Char(
        string="Cloudinary Upload Folder",
        config_parameter="blogcreator.cloudinary_upload_folder",
        default="blogcreator",
    )

    include_debug_info = fields.Boolean(
        string="Include Debug Info in Webhook",
        config_parameter="blogcreator.include_debug_info",
        default=False,
    )

    export_fields = fields.Char(
        string="Fields to Export",
        config_parameter="blogcreator.export_fields",
        default="id,title,content,cloudinary_content,note_type,tags,is_published,create_date,user,main_image,content_images",
        help="Comma-separated list of fields to include in the webhook payload",
    )

    def test_cloudinary_connection(self):
        """Test the Cloudinary connection"""
        try:
            cloudinary.config(
                cloud_name=self.cloudinary_cloud_name,
                api_key=self.cloudinary_api_key,
                api_secret=self.cloudinary_api_secret,
            )

            result = cloudinary.api.ping()
            if result.get("status") == "ok":
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Connection Successful",
                        "message": "Successfully connected to Cloudinary!",
                        "sticky": False,
                        "type": "success",
                    },
                }
        except Exception as e:
            _logger.error(f"Cloudinary connection error: {str(e)}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connection Failed",
                    "message": str(e),
                    "sticky": True,
                    "type": "danger",
                },
            }
