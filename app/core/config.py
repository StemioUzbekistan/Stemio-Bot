import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram Bot Settings ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Exode API Settings ---
EXODE_API_BASE_URL = "https://api.exode.biz/saas/v2" 
SELLER_ID = os.getenv('SELLER_ID')
EXODE_TOKEN = os.getenv('EXODE_TOKEN')
SCHOOL_ID = os.getenv('SCHOOL_ID')
COURSES_SHEET_ID = os.getenv('COURSES_SHEET_ID')
SUPPORT_GROUP_ID = os.getenv('SUPPORT_GROUP_ID')

# --- Google Sheets Settings ---
# ID for the sheet with registration data (parents, children)
REGISTRATION_SHEET_ID = os.getenv('REGISTRATION_SHEET_ID')
# ID for the sheet with the university directory
UNIVERSITIES_SHEET_ID = os.getenv('UNIVERSITIES_SHEET_ID')
# Path to the credentials file, which is in the project root
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
# ID for the sheet with the professions directory
PROFESSIONS_SHEET_ID = os.getenv('PROFESSIONS_SHEET_ID') 
# ID for the sheet with private universities
PRIVATE_UNIVERSITIES_SHEET_ID = os.getenv('PRIVATE_UNIVERSITIES_SHEET_ID')
FOREIGN_UNIVERSITIES_SHEET_ID = os.getenv('FOREIGN_UNIVERSITIES_SHEET_ID')

# ID таблиц для ГОСУДАРСТВЕННЫХ вузов, сгруппированные по городам
STATE_UNIVERSITIES_BY_CITY = {
    "Ташкент": os.getenv('TASHKENT_STATE_UNIVERSITIES_ID'),
    "Андижан": os.getenv('ANDIJAN_STATE_UNIVERSITIES_ID'),
    "Бухара": os.getenv('BUKHARA_STATE_UNIVERSITIES_ID'),
    "Джизак": os.getenv('JIZZAKH_STATE_UNIVERSITIES_ID'),
    "Кашкадарья": os.getenv('KASHKADARYA_STATE_UNIVERSITIES_ID'),
    "Навои": os.getenv('NAVOI_STATE_UNIVERSITIES_ID'),
    "Наманган": os.getenv('NAMANGAN_STATE_UNIVERSITIES_ID'),
    "Самарканд": os.getenv('SAMARKAND_STATE_UNIVERSITIES_ID'),
    "Сурхандарья": os.getenv('SURKHANDARYA_STATE_UNIVERSITIES_ID'),
    "Сырдарья": os.getenv('SIRDARYA_STATE_UNIVERSITIES_ID'),
    "Фергана": os.getenv('FERGHANA_STATE_UNIVERSITIES_ID'),
    "Хорезм": os.getenv('KHOREZM_STATE_UNIVERSITIES_ID'),
    "Каракалпакстан": os.getenv('KARAKALPAKSTAN_STATE_UNIVERSITIES_ID'),
}
