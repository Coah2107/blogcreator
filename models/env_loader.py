# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from pathlib import Path

# Tìm file .env
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Lấy các biến môi trường Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
CLOUDINARY_UPLOAD_FOLDER = os.getenv("CLOUDINARY_UPLOAD_FOLDER", "blogcreator")

# Lấy các biến môi trường webhook
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")