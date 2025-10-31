import logging
from datetime import datetime 
from typing import List, Dict, Optional, Any
import gspread
from google.oauth2.service_account import Credentials
from app.core.config import GOOGLE_SHEETS_CREDENTIALS_PATH

try:
    from app.utils.test_content import SCALES_INFO
except ImportError:
    SCALES_INFO = {} 

logger = logging.getLogger(__name__)

# Области доступа для Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsManager:
    """Базовый класс для работы с Google Sheets."""
    
    def __init__(self, sheet_id: str):
        self.sheet_id = sheet_id
        self.client = None
        self.sheet = None
        if sheet_id: 
            self._connect()
    
    def _connect(self):
        """Подключение к Google Sheets."""
        try:
            creds = Credentials.from_service_account_file(
                GOOGLE_SHEETS_CREDENTIALS_PATH,
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.sheet_id)
            logger.info(f"Successfully connected to Google Sheet: {self.sheet_id}")
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise
    
    def get_all_records(self, worksheet_name: Optional[str] = None) -> List[Dict]:
        """Получение всех записей из листа."""
        try:
            if worksheet_name:
                worksheet = self.sheet.worksheet(worksheet_name)
            else:
                worksheet = self.sheet.get_worksheet(0) 
            
            return worksheet.get_all_records()
        except gspread.exceptions.WorksheetNotFound:
             logger.error(f"Worksheet (вкладка) с именем '{worksheet_name}' не найдена.")
             return []
        except Exception as e:
            logger.error(f"Error getting records from {worksheet_name or 'default sheet'}: {e}")
            return []
    
    def append_row(self, values: List, worksheet_name: Optional[str] = None):
        """Добавление новой строки в таблицу."""
        try:
            worksheet = self.sheet.worksheet(worksheet_name) if worksheet_name else self.sheet.get_worksheet(0)
            worksheet.append_row(values)
            logger.info(f"Row appended to {worksheet_name or 'default sheet'}")
        except Exception as e:
            logger.error(f"Error appending row to {worksheet_name or 'default sheet'}: {e}")
    
    def update_cell(self, row: int, col: int, value: Any, worksheet_name: Optional[str] = None):
        """Обновление конкретной ячейки."""
        try:
            worksheet = self.sheet.worksheet(worksheet_name) if worksheet_name else self.sheet.get_worksheet(0)
            worksheet.update_cell(row, col, value)
            logger.info(f"Cell ({row}, {col}) updated in {worksheet_name or 'default sheet'}")
        except Exception as e:
            logger.error(f"Error updating cell in {worksheet_name or 'default sheet'}: {e}")


class RegistrationGSheet(GoogleSheetsManager):
    """Класс для работы с таблицей регистрации пользователей."""
    
    def __init__(self, sheet_id: str):
        super().__init__(sheet_id)
        self.parent_worksheet = 'Родитель'
        self.student_worksheet = 'Ученик'
        self.children_worksheet = 'Родитель-Ребенок'
    
    def get_user_by_id(self, telegram_id: int) -> Optional[Dict]:
        """Поиск пользователя по Telegram ID."""
        try:
            # Ищем среди родителей
            parents = self.get_all_records(self.parent_worksheet)
            for parent in parents:
                if str(parent.get('Telegram ID')) == str(telegram_id):
                    parent['role'] = 'parent'
                    return parent
            
            # Ищем среди студентов
            students = self.get_all_records(self.student_worksheet)
            for student in students:
                if str(student.get('Telegram ID')) == str(telegram_id):
                    student['role'] = 'student'
                    return student
                    
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def add_parent(self, data: Dict) -> bool:
        """Добавление нового родителя."""
        try:
            # Убеждаемся, что 'role' есть в словаре
            if 'role' not in data:
                data['role'] = 'parent'

            # Собираем значения в ПРАВИЛЬНОМ ПОРЯДКЕ, 
            # используя ключи из FSM (`parent_first_name` и т.д.)
            values = [
                data.get('telegram_id', ''),         # Колонка A: Telegram ID
                data.get('parent_first_name', ''),   # Колонка B: Имя
                data.get('parent_last_name', ''),    # Колонка C: Фамилия
                data.get('parent_phone', ''),        # Колонка D: Номер телефон
                data.get('parent_email', ''),        # Колонка E: Email
                data.get('language', 'ru'),          # Колонка F: Язык
                data.get('role', 'parent'),          # Колонка G: role
                datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Колонка H: Время
            ]
            self.append_row(values, self.parent_worksheet)
            return True
        except Exception as e:
            logger.error(f"Error adding parent: {e}")
            return False

    def add_student(self, data: Dict) -> bool:
        """Добавление нового студента."""
        try:
            # Убеждаемся, что 'role' есть в словаре
            if 'role' not in data:
                data['role'] = 'student'
                
            # Собираем значения, используя ключи из FSM
            # (Предполагается, что у "Ученик" колонки A-K)
            values = [
                data.get('Telegram ID', data.get('telegram_id', '')), # A
                data.get('Имя', data.get('student_first_name', '')), # B
                data.get('Фамилия', data.get('student_last_name', '')), # C
                data.get('Дата рождения', data.get('student_dob', '')), # D
                data.get('Город', data.get('student_city', '')), # E
                data.get('Телефон', data.get('student_phone', '')), # F
                data.get('Язык', data.get('language', 'ru')), # G
                data.get('role', 'student'), # H
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # I
                data.get('Имя родителя', data.get('parent_name', '')), # J
                data.get('Телефон родителя', data.get('parent_phone', '')) # K
            ]
            self.append_row(values, self.student_worksheet)
            return True
        except Exception as e:
            logger.error(f"Error adding student: {e}")
            return False
    
    def add_child(self, parent_id: int, data: Dict) -> bool:
        """Добавление ребенка к родителю."""
        try:
            # Приводим дату к ДД.ММ.ГГГГ, если она YYYY-MM-DD
            dob = data.get('child_dob', '')
            if dob and '-' in dob:
                try:
                    dob = datetime.strptime(dob, '%Y-%m-%d').strftime('%d.%m.%Y')
                except:
                    pass # Оставляем как есть, если формат неверный
            
            # Собираем интересы (если они есть)
            interests_list = data.get('child_interests', [])
            interests_str = ", ".join(interests_list) if isinstance(interests_list, list) else data.get('child_interests', '')

            values = [
                str(parent_id),
                data.get('child_first_name', ''),
                data.get('child_last_name', ''),
                dob,
                data.get('child_class', ''),
                data.get('child_city', ''),
                interests_str, # Колонка 'Интересы'
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # Время регистрации
                data.get('exode_user_id', ''), # 'Exode ID'
                data.get('child_phone', '') # 'Телефон ребенка'
            ]
            self.append_row(values, self.children_worksheet)
            return True
        except Exception as e:
            logger.error(f"Error adding child: {e}")
            return False
    

    def get_children_by_parent_id(self, parent_id: int) -> List[Dict]:
        """Получение списка детей родителя."""
        try:
            children = self.get_all_records(self.children_worksheet)
            return [
                child for child in children 

                if str(child.get('Parent Telegram ID')) == str(parent_id)
            ]
        except Exception as e:
            logger.error(f"Error getting children: {e}")
            return []

    
    def update_user_data(self, user_id: int, field_name: str, new_value: str) -> bool:
        """Обновление данных пользователя."""
        try:
            user_data = self.get_user_by_id(user_id)
            if not user_data:
                return False
            
            worksheet_name = self.parent_worksheet if user_data['role'] == 'parent' else self.student_worksheet
            worksheet = self.sheet.worksheet(worksheet_name)
            
            records = worksheet.get_all_records()
            row_index = None
            
            for i, record in enumerate(records, start=2):
                if str(record.get('Telegram ID')) == str(user_id):
                    row_index = i
                    break
            
            if row_index:
                headers = worksheet.row_values(1)
                if field_name in headers:
                    col_index = headers.index(field_name) + 1
                    worksheet.update_cell(row_index, col_index, new_value)
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error updating user data: {e}")
            return False
    
    def get_student_parent_contact(self, student_id: int) -> Optional[str]:
        """Получение контакта родителя студента."""
        try:
            students = self.get_all_records(self.student_worksheet)
            for student in students:
                if str(student.get('Telegram ID')) == str(student_id):
                    parent_name = student.get('Имя родителя', '')
                    parent_phone = student.get('Телефон родителя', '')
                    if parent_name or parent_phone:
                        return f"{parent_name} {parent_phone}".strip()
            return None
        except Exception as e:
            logger.error(f"Error getting parent contact: {e}")
            return None


class UniversitiesGSheet(GoogleSheetsManager):

    
    def __init__(self, sheet_id: str):
        # Инициализируем клиент, но не открываем конкретный sheet
        self.client = None
        if sheet_id: # sheet_id здесь - "фиктивный", для инициализации
            try:
                creds = Credentials.from_service_account_file(
                    GOOGLE_SHEETS_CREDENTIALS_PATH,
                    scopes=SCOPES
                )
                self.client = gspread.authorize(creds)
                # Открываем "фиктивную" таблицу (e.g., REGISTRATION_SHEET_ID)
                self.sheet = self.client.open_by_key(sheet_id) 
                logger.info(f"UniversitiesGSheet manager initialized with base sheet: {sheet_id}")
            except Exception as e:
                logger.error(f"Failed to initialize UniversitiesGSheet manager: {e}")
                raise
    
    def _open_sheet_by_id(self, sheet_id: str):
        """Внутренний метод для открытия (или переключения) таблицы по ID."""
        try:
            self.sheet = self.client.open_by_key(sheet_id)
            logger.info(f"Switched to Google Sheet: {sheet_id}")
            return True
        except gspread.exceptions.SpreadsheetNotFound:
             logger.error(f"Spreadsheet with ID {sheet_id} not found or no access.")
             self.sheet = None
             return False
        except Exception as e:
            logger.error(f"Failed to open sheet by ID {sheet_id}: {e}")
            self.sheet = None # Сбрасываем, если не удалось
            return False
    
    def get_universities_by_city_and_type(self, sheet_id: str, city: str = None) -> List[Dict]:

        try:
            # <-- Переключаемся на нужную таблицу (e.g., Tashkent)
            if not self._open_sheet_by_id(sheet_id): 
                return []

            universities = self.get_all_records("Universities") 

            
            if city:
                # Фильтруем по городу (важно для Частных и Иностранных)
                universities = [
                    uni for uni in universities 
                    if uni.get('Город', '').lower() == city.lower()
                ]
            
            return universities
        except Exception as e:
            logger.error(f"Error getting universities: {e}")
            return []
    

    def get_faculties_by_sheet_name(self, sheet_name: str) -> List[Dict]:

        if not self.sheet:
            logger.error("No sheet is currently open. Call get_universities... first.")
            return []
            
        try:
            # Ищем вкладку (worksheet) по ее ИМЕНИ (e.g., "НацУнивер")
            worksheet = self.sheet.worksheet(sheet_name)
            # Получаем все строки из этой вкладки
            faculties_and_programs = worksheet.get_all_records()
            logger.info(f"Successfully loaded {len(faculties_and_programs)} programs from worksheet '{sheet_name}'")
            
            # Возвращаем список словарей (1 строка = 1 программа)
            return faculties_and_programs
            
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet (вкладка) с именем '{sheet_name}' не найдена в файле {self.sheet.title}.")
            return []
        except Exception as e:
            logger.error(f"Error getting faculties from worksheet '{sheet_name}': {e}")
            return []



class CoursesGSheet(GoogleSheetsManager):
    """Класс для работы с таблицей курсов."""
    
    def __init__(self, sheet_id: str):
        super().__init__(sheet_id)

        self.worksheet_name = 'Courses' 


    def get_courses(self, category: str = None, subcategory: str = None, language: str = None) -> List[Dict]:
        """Получение списка курсов с фильтрацией."""
        try:
            courses = self.get_all_records(self.worksheet_name) # Используем self.worksheet_name
            
            # Применяем фильтры
            if category:
                courses = [c for c in courses if c.get('Категория') == category]
            if subcategory:
                courses = [c for c in courses if c.get('Подкатегория') == subcategory]
            if language:
                courses = [c for c in courses if c.get('language') == language]
            
            return courses
        except Exception as e:
            logger.error(f"Error getting courses: {e}")
            return []
    
    def get_course_by_id(self, course_id: str) -> Optional[Dict]:
        """Получение курса по ID."""
        try:
            courses = self.get_all_records(self.worksheet_name) # Используем self.worksheet_name
            for course in courses:
                if str(course.get('course_id')) == str(course_id):
                    return course
            return None
        except Exception as e:
            logger.error(f"Error getting course by ID: {e}")
            return None


class ProfessionsGSheet(GoogleSheetsManager):

    def get_professions_by_scale(self, scale_key: str) -> List[Dict]:
        """
        Получение профессий по ключу шкалы (scale_key ИСПОЛЬЗУЕТСЯ КАК ИМЯ ЛИСТА).
        """
        try:
            # Используем scale_key (e.g., "human", "tech") как имя листа (worksheet_name)
            professions = self.get_all_records(worksheet_name=scale_key)
            return professions
        except Exception as e:
            # Если лист не найден (например, 'sign' вместо 'sign'), gspread выдаст ошибку
            logger.error(f"Error getting professions from worksheet '{scale_key}': {e}")
            return []
    
    def get_profession_by_name(self, name: str, worksheet_name: str) -> Optional[Dict]:
        """Получение профессии по названию с конкретного листа."""
        try:
            professions = self.get_all_records(worksheet_name)
            for prof in professions:
                if prof.get('Название профессии') == name:
                    return prof
            return None
        except Exception as e:
            logger.error(f"Error getting profession by name from {worksheet_name}: {e}")
            return None
    
    def get_all_professions(self) -> List[Dict]:

        all_professions = []
        try:
            # Получаем список всех листов в таблице
            sheet_names = [ws.title for ws in self.sheet.worksheets()]
            
            # Фильтруем, оставляя только листы со шкалами
            scale_sheets = [name for name in sheet_names if name in ['human', 'tech', 'art', 'sign', 'nature']]

            for sheet_name in scale_sheets:
                try:
                    logger.info(f"Loading professions from sheet: {sheet_name}")
                    all_professions.extend(self.get_all_records(sheet_name))
                except Exception as e:
                    logger.error(f"Failed to load professions from sheet '{sheet_name}': {e}")
                    # Просто пропускаем этот лист и идем к следующему
                    pass

            
            return all_professions
        except Exception as e:
            logger.error(f"Error getting all professions from all sheets: {e}")
            return []

    def get_all_directions(self) -> List[str]:
        """Получение списка всех уникальных направлений со всех листов."""
        try:
            all_professions = self.get_all_professions()
            directions = set()
            
            for prof in all_professions:
                if direction := prof.get('Направление'):
                    directions.add(direction)
            
            return sorted(list(directions))
        except Exception as e:
            logger.error(f"Error getting all directions: {e}")
            return []


# Вспомогательные функции для обратной совместимости
def get_user_data(telegram_id: int, sheet_id: str) -> Optional[Dict]:
    """Получение данных пользователя (для обратной совместимости)."""
    manager = RegistrationGSheet(sheet_id)
    return manager.get_user_by_id(telegram_id)


def save_user_data(data: Dict, sheet_id: str) -> bool:
    """Сохранение данных пользователя (для обратной совместимости)."""
    manager = RegistrationGSheet(sheet_id)
    
    if data.get('role') == 'parent':
        return manager.add_parent(data)
    elif data.get('role') == 'student':
        return manager.add_student(data)
    
    return False

