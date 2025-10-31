from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_share_phone_keyboard(lexicon: dict, lang: str) -> types.ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(
            text=lexicon[lang]['button-share-phone'],
            request_contact=True
        )
    )
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_parent_main_menu_keyboard(lexicon: dict, lang: str) -> types.ReplyKeyboardMarkup:
    """Создает клавиатуру главного меню для РОДИТЕЛЯ."""
    print("--- СОЗДАЕТСЯ МЕНЮ ДЛЯ РОДИТЕЛЯ ---")
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-navigator']),
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-programs'])
    )
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-universities']),
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-professions']) 
    )
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-my-children']),
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-profile'])
    )
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-support'])
    )
    return builder.as_markup(resize_keyboard=True, is_persistent=True)

def get_student_main_menu_keyboard(lexicon: dict, lang: str) -> types.ReplyKeyboardMarkup:
    """Создает клавиатуру главного меню для УЧЕНИКА."""
    print("--- СОЗДАЕТСЯ МЕНЮ ДЛЯ УЧЕНИКА ---")
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-student-main-menu-navigator']),
        types.KeyboardButton(text=lexicon[lang]['button-student-main-menu-programs'])
    )
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-student-main-menu-universities']),
        types.KeyboardButton(text=lexicon[lang]['button-main-menu-professions']) 
    )
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-student-main-menu-ai']),
        types.KeyboardButton(text=lexicon[lang]['button-student-main-menu-profile'])
    )
    builder.row(
        types.KeyboardButton(text=lexicon[lang]['button-student-main-menu-support'])
    )

    return builder.as_markup(resize_keyboard=True, is_persistent=True)


