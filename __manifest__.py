# -*- coding: utf-8 -*-
{
    "name": "blogcreator",
    "summary": """
       Short (1 phrase/line) summary of the module's purpose, used as
       subtitle on modules listing or apps.openerp.com""",
    "description": """
       Long description of module's purpose
   """,
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.1",
    "depends": ["base", "mail"],
    "external_dependencies": {
        "python": ["cloudinary", "bs4"],  # Thêm cloudinary vào đây
    },
    "data": [
        "security/blogcreator_security.xml",
        "security/ir.model.access.csv",
        "views/views.xml",
        "views/templates.xml",
        "views/menu.xml",
        "views/res_config_settings_views.xml",
        "views/n8n_response_views.xml",
        "data/n8n_sequence.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
    "installable": True,
    "application": True,
    "assets": {
        "web.assets_backend": [
            "blogcreator/static/src/js/wysiwyg_extend.js",
        ],
    },
}
