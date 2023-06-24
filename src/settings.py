import os

from dotenv import load_dotenv


load_dotenv()


TOKEN = os.getenv('API_TOKEN') or ''
PATH = os.getenv('API_ENDPOINT') or ''
if not TOKEN or not PATH:
    raise RuntimeError('Invalid .env')

IMGUR_ID = os.getenv('IMGUR_CLIENT_ID') or ''
IMGUR_TOKEN = os.getenv('IMGUR_TOKEN') or ''
