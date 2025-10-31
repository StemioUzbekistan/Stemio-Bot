from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar

from app.utils.locations import CITIES_RU, CITIES_UZ

# --- ОБЩИЕ КЛАВИАТУРЫ ---

def get_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇺🇿 Oʻzbek", callback_data="lang_uz")
    )
    return builder.as_markup()

def get_role_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-parent'], callback_data="role_parent"),
        InlineKeyboardButton(text=lexicon[lang]['button-student'], callback_data="role_student")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_lang_select"))
    return builder.as_markup()

def get_profile_creation_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-yes-create-profile'], callback_data="create_profile")
    ).row(
        InlineKeyboardButton(text=lexicon[lang]['button-later'], callback_data="postpone_creation")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_role_select"))
    return builder.as_markup()

def get_city_keyboard(lang: str):
    cities_list = CITIES_UZ if lang == 'uz' else CITIES_RU
    builder = InlineKeyboardBuilder()
    for city in cities_list:
        builder.add(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="⌨️ Ввести город вручную", callback_data="manual_city_input"))
    return builder.as_markup()

async def get_calendar_with_manual_input_keyboard(lexicon: dict, lang: str):
    calendar_markup = await SimpleCalendar().start_calendar(year=2010)
    manual_input_button = InlineKeyboardButton(
        text="⌨️ Ввести дату вручную",
        callback_data="manual_dob_input"
    )
    calendar_markup.inline_keyboard.append([manual_input_button])
    return calendar_markup


# --- КЛАВИАТУРЫ ДЛЯ СЦЕНАРИЕВ ---

def get_skip_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-skip'], callback_data="skip_email")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_phone_input"))
    return builder.as_markup()

def get_profile_confirmation_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-confirm'], callback_data="confirm_profile"),
        InlineKeyboardButton(text=lexicon[lang]['button-edit'], callback_data="edit_profile")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_email_input"))
    return builder.as_markup()

def get_add_child_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-add-child'], callback_data="add_child")
    ).row(
        InlineKeyboardButton(
            text=lexicon[lang]['button-not-add-child-yet'], 
            callback_data="finish_registration"
        )
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_profile_confirmation"))
    return builder.as_markup()

def get_interests_keyboard(lexicon: dict, lang: str, chosen_interests: set = None) -> InlineKeyboardMarkup:
    """(ИСПРАВЛЕНО) Клавиатура для выбора интересов с кнопкой 'Назад'."""
    if chosen_interests is None:
        chosen_interests = set()
    
    builder = InlineKeyboardBuilder()
    
    interest_keys = lexicon[lang]['interest-benefits'].keys()
    
    for interest_key in interest_keys:
        interest_text = lexicon[lang].get(f'button-{interest_key}', interest_key.capitalize())
        emoji = "✅" if interest_key in chosen_interests else "⚪️"
        builder.row(InlineKeyboardButton(
            text=f"{emoji} {interest_text}", 
            callback_data=f"interest_{interest_key}"
        ))

    builder.row(
        InlineKeyboardButton(
            text=lexicon[lang]['button-back'], 
            callback_data="back_to_class_input" 
        ),
        InlineKeyboardButton(
            text=lexicon[lang].get('button-done', 'Готово'),
            callback_data="interests_done"
        )
    )  
    return builder.as_markup()

def get_child_confirmation_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-confirm'], callback_data="confirm_child")
    ).row(
        InlineKeyboardButton(text=lexicon[lang]['button-add-another-child'], callback_data="add_another_child")
    ).row(
        InlineKeyboardButton(text=lexicon[lang]['button-go-to-main-menu'], callback_data="main_menu")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_interests"))
    return builder.as_markup()

def get_quick_benefit_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-find-courses'], callback_data="find_courses"),
        InlineKeyboardButton(text=lexicon[lang]['button-go-to-main-menu'], callback_data="main_menu")
    )
    return builder.as_markup()

def get_student_welcome_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-yes-lets-go'], callback_data="student_create_profile")
    ).row(
        InlineKeyboardButton(text=lexicon[lang]['button-later'], callback_data="postpone_registration")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_role_select"))
    return builder.as_markup()

def get_student_goal_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-goal-university'], callback_data="goal_university"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-goal-grades'], callback_data="goal_grades"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-goal-profession'], callback_data="goal_profession"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-goal-explore'], callback_data="goal_explore"))
    return builder.as_markup()

def get_student_skip_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-skip'], callback_data="skip_parent_contact"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_phone_input"))
    return builder.as_markup()

def get_student_profile_confirmation_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-confirm'], callback_data="student_confirm_profile"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-edit'], callback_data="student_edit_profile"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_parent_contact"))
    return builder.as_markup()

def get_improve_grades_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-find-subject-courses'], callback_data="find_subject_courses")
    ).row(
        InlineKeyboardButton(text=lexicon[lang]['button-see-ai-assistant'], callback_data="see_ai_assistant")
    ).row(
        InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_goal_select")
    )
    return builder.as_markup()
    
def get_explore_courses_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-show-intro-courses'], callback_data="show_intro_courses")
    ).row(
        InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_goal_select")
    )
    return builder.as_markup()


# --- КЛАВИАТУРЫ ДЛЯ ПРОФИЛЯ И РЕДАКТИРОВАНИЯ ---

def get_profile_keyboard(lexicon: dict, lang: str, is_parent: bool):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-edit-profile'], callback_data="edit_profile_action"))
    if is_parent:
        builder.row(InlineKeyboardButton(text=lexicon[lang]['button-manage-children'], callback_data="manage_children_action"))
    else:
        builder.row(InlineKeyboardButton(text=lexicon[lang]['button-my-courses'], callback_data="my_courses_action"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_main_menu"))
    return builder.as_markup()
    

def get_edit_profile_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Имя", callback_data="edit_field_parent_Имя"))
    builder.row(InlineKeyboardButton(text="Фамилия", callback_data="edit_field_parent_Фамилия"))
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-edit-phone'], callback_data="edit_field_parent_Номер телефон"),
        InlineKeyboardButton(text=lexicon[lang]['button-edit-email'], callback_data="edit_field_parent_Email")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_profile_view"))
    return builder.as_markup()

    
def get_student_edit_profile_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Имя", callback_data="edit_field_student_Имя"),
        InlineKeyboardButton(text="Фамилия", callback_data="edit_field_student_Фамилия")
    )
    builder.row(
        InlineKeyboardButton(text="Дата рождения", callback_data="edit_field_student_Дата рождения"),
        InlineKeyboardButton(text=lexicon[lang]['button-edit-city'], callback_data="edit_field_student_Город")
    )
    builder.row(
        InlineKeyboardButton(text="Телефон", callback_data="edit_field_student_Телефон"),
        InlineKeyboardButton(text=lexicon[lang]['button-edit-parent-contact'], callback_data="edit_field_student_Телефон родителя") # Пример, укажите правильное имя колонки
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_profile_view"))
    return builder.as_markup()


def get_edit_profile_choices_keyboard(lexicon: dict, lang: str, is_parent: bool):
    if is_parent:
        return get_edit_profile_keyboard(lexicon, lang)
    else:
        return get_student_edit_profile_keyboard(lexicon, lang)


def get_children_list_keyboard(children: list, lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    for index, child in enumerate(children):
        child_name = f"{child.get('Имя ребенка', '')} {child.get('Фамилия ребенка', '')}".strip()
        if not child_name:
            child_name = "Имя не указано"
        
        builder.row(InlineKeyboardButton(
            text=child_name, 
            callback_data=f"view_child_{index}" 
        ))
        
    builder.row(InlineKeyboardButton(
        text=lexicon[lang]['button-back'], 
        callback_data="back_to_profile_view"
    ))
    return builder.as_markup()


def get_back_to_children_list_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_children_list"))
    return builder.as_markup()


# --- КЛАВИАТУРЫ ДЛЯ STEM-НАВИГАТОРА ---

def get_start_test_keyboard(lexicon: dict, lang: str, from_profession_branch: bool = False):
    builder = InlineKeyboardBuilder()
    start_button_text = lexicon[lang]['button-pass-test'] if from_profession_branch else lexicon[lang]['button-start-test-now']
    builder.row(InlineKeyboardButton(text=start_button_text, callback_data="start_test_now"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-do-it-later'], callback_data="postpone_action"))
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_goal_select"))
    return builder.as_markup()

def get_about_test_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-start-test'], callback_data="begin_stem_test"),
        InlineKeyboardButton(text=lexicon[lang]['button-cancel'], callback_data="postpone_action")
    )
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="postpone_action"))
    return builder.as_markup()

def get_subcategories_keyboard(subcategories: dict, scale_key: str):
    builder = InlineKeyboardBuilder()
    for subcat_key, subcat_value in subcategories.items():
        builder.row(InlineKeyboardButton(text=subcat_value['title'], callback_data=f"subcat_{scale_key}_{subcat_key}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к результатам", callback_data="back_to_results"))
    return builder.as_markup()

def get_professions_list_keyboard(professions: list, scale_key: str, subcat_key: str):
    builder = InlineKeyboardBuilder()
    for i, prof in enumerate(professions):
        builder.row(InlineKeyboardButton(text=prof['title'], callback_data=f"prof_{scale_key}_{subcat_key}_{i}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data=f"view_professions_{scale_key}"))
    return builder.as_markup()

def get_profession_card_keyboard(website_link: str, scale_key: str, subcat_key: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔗 Узнать больше на сайте", url=website_link))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к списку профессий", callback_data=f"subcat_{scale_key}_{subcat_key}"))
    return builder.as_markup()


def get_yes_no_keyboard(lexicon: dict, lang: str, yes_callback: str = "yes", no_callback: str = "no"):
    """Creates a universal Yes/No keyboard with customizable callback_data."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon[lang]['button-yes'], callback_data=yes_callback),
        InlineKeyboardButton(text=lexicon[lang]['button-no'], callback_data=no_callback)
    )
    return builder.as_markup()

def get_consent_keyboard(lexicon: dict, lang: str):
    """Создает клавиатуру для получения согласия на создание профиля в Exode."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=lexicon[lang]['button-yes-create-exode'],
            callback_data="consent_yes"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=lexicon[lang]['button-later'], 
            callback_data="consent_no"
        )
    )
    return builder.as_markup()

# --- КЛАВИАТУРЫ ДЛЯ РАЗДЕЛОВ ГЛАВНОГО МЕНЮ ---

def get_section_keyboard(lexicon: dict, lang: str, section: str, is_parent: bool = False): 
    builder = InlineKeyboardBuilder()
    
    if section == 'navigator':
        callback_data = "parent_start_test_selection" if is_parent else "student_start_test_info"
        builder.row(InlineKeyboardButton(text="Пройти/посмотреть результаты", callback_data=callback_data))
    
    elif section == 'programs':
        builder.row(InlineKeyboardButton(text="Смотреть каталог курсов", callback_data="action_view_courses"))
    elif section == 'ai_assistant':
        builder.row(InlineKeyboardButton(text="Задать вопрос ИИ", callback_data="action_ask_ai"))
    elif section == 'universities':
        builder.row(InlineKeyboardButton(text="Искать вуз по фильтрам", callback_data="action_filter_unis"))
    elif section == 'my_children':
        builder.row(InlineKeyboardButton(text="Добавить ребёнка", callback_data="action_add_child"))
    
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_main_menu"))
    return builder.as_markup()

def add_back_button(builder: InlineKeyboardBuilder, lexicon: dict, lang: str, callback_data: str = "back"):
    """Добавляет кнопку 'Назад' в клавиатуру"""
    builder.row(InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data=callback_data))
    return builder


def get_parent_start_test_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=lexicon[lang]['button-start-test'], 
        callback_data="begin_stem_test"
    ))
    builder.row(InlineKeyboardButton(
        text=lexicon[lang]['button-later'], 
        callback_data="back_to_main_menu"
    ))
    return builder.as_markup()

# --- 1. Клавиатура для Категорий (Программирование, Математика) ---
def get_course_categories_keyboard(categories: list, lexicon: dict, lang: str):
    """Создает клавиатуру со списком категорий (Программирование, Математика)."""
    builder = InlineKeyboardBuilder()
    for cat in sorted(categories):
        builder.row(types.InlineKeyboardButton(text=cat, callback_data=f"category_{cat}"))
    builder.row(types.InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_main_menu"))
    return builder.as_markup()


# --- 2. Клавиатура для Подкатегорий (Python, C++) ---
def get_course_subcategories_keyboard(subcategories: list, lexicon: dict, lang: str):
    """Создает клавиатуру со списком подкатегорий (Python, C++, Web)."""
    builder = InlineKeyboardBuilder()
    for subcat in sorted(subcategories):
        builder.row(types.InlineKeyboardButton(text=subcat, callback_data=f"subcategory_{subcat}"))
    builder.row(types.InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_categories"))
    return builder.as_markup()


# --- 3. Клавиатура для конкретных Курсов (Python Базовый, Python Средний) ---
def get_specific_courses_keyboard(courses: list, lexicon: dict, lang: str):
    """Создает клавиатуру со списком конкретных курсов."""
    builder = InlineKeyboardBuilder()
    for i, course in enumerate(courses):
        builder.row(types.InlineKeyboardButton(text=course['Название курса'], callback_data=f"course_{i}"))
    builder.row(types.InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_subcategories"))
    return builder.as_markup()

def get_course_card_keyboard(lexicon: dict, lang: str, course_id: str):
    """Эта функция нужна для финальной карточки курса."""
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="✍️ Записаться на курс",
        callback_data=f"enroll_{course_id}"
    ))
    builder.row(types.InlineKeyboardButton(
        text=lexicon[lang]['button-back'],
        callback_data="back_to_subcategories" 
    ))
    return builder.as_markup()
