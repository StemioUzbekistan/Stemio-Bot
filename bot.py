import asyncio
import logging
from os import getenv
import json

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import BotCommand
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from aiogram.filters import CommandStart, Command 

# --- ИМПОРТЫ ---
from app.utils.google_sheets import RegistrationGSheet, UniversitiesGSheet, CoursesGSheet, ProfessionsGSheet
from app.core.config import (
    REGISTRATION_SHEET_ID, COURSES_SHEET_ID, PRIVATE_UNIVERSITIES_SHEET_ID, 
    FOREIGN_UNIVERSITIES_SHEET_ID, PROFESSIONS_SHEET_ID, STATE_UNIVERSITIES_BY_CITY
)

from app.states.registration import GeneralRegistration, ParentRegistration, StudentRegistration
from app.keyboards.inline import get_language_keyboard, get_role_keyboard, get_profile_creation_keyboard, get_student_welcome_keyboard
from app.keyboards.reply import get_parent_main_menu_keyboard, get_student_main_menu_keyboard
from app.handlers.registration import parent as parent_router_module
from app.handlers.registration import student as student_router_module
from app.handlers import parent_actions as parent_actions_router_module
from app.handlers import programs as programs_router_module
from app.handlers import universities as universities_router_module
from app.handlers import profile as profile_router_module
from app.handlers import stem_navigator as stem_navigator_router_module
from app.handlers import main_menu as main_menu_router_module
from app.handlers import support as support_router_module
from app.handlers import professions as professions_router_module

async def set_main_menu(bot: Bot, lexicon: dict):
    """Создает и устанавливает меню быстрых команд (slash commands)."""
    commands_ru = [
        BotCommand(command="/start", description="🚀 Перезапустить / Главное меню"),
        BotCommand(command="/menu", description="🏠 Главное меню"),
        BotCommand(command="/profile", description="👤 Мой профиль"),
        BotCommand(command="/support", description="💬 Поддержка")
    ]
    await bot.set_my_commands(commands_ru, language_code="ru")
    commands_uz = [
        BotCommand(command="/start", description="🚀 Qayta boshlash / Bosh menyu"),
        BotCommand(command="/menu", description="🏠 Bosh menyu"),
        BotCommand(command="/profile", description=lexicon['uz'].get('button-student-main-menu-profile', '👤 Profil')),
        BotCommand(command="/support", description=lexicon['uz'].get('button-student-main-menu-support', '💬 Qo\'llab-quvvatlash'))
    ]
    await bot.set_my_commands(commands_uz, language_code="uz")

async def main() -> None:
    load_dotenv()
    TOKEN = getenv("BOT_TOKEN")
    if not TOKEN:
        logging.critical("Токен бота не найден!")
        return

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    with open('texts.json', 'r', encoding='utf-8') as f:
        lexicon = json.load(f)
    dp['lexicon'] = lexicon
    await set_main_menu(bot, lexicon)
    try:
        registration_manager = RegistrationGSheet(REGISTRATION_SHEET_ID)
        courses_manager = CoursesGSheet(COURSES_SHEET_ID)
        professions_manager = ProfessionsGSheet(PROFESSIONS_SHEET_ID)
        universities_manager = UniversitiesGSheet(REGISTRATION_SHEET_ID)

        dp['registration_manager'] = registration_manager
        dp['universities_manager'] = universities_manager
        dp['courses_manager'] = courses_manager
        dp['professions_manager'] = professions_manager
        dp['state_uni_ids_by_city'] = STATE_UNIVERSITIES_BY_CITY
        
        logging.info("Менеджеры Google Sheets успешно инициализированы.")
        
    except Exception as e:
        logging.critical(f"КРИТИЧЕСКАЯ ОШИБКА при подключении к Google Sheets: {e}", exc_info=True)
        return 

    # --- Устанавливаем ПРАВИЛЬНЫЙ ПОРЯДОК ПОДКЛЮЧЕНИЯ ---
    
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message, state: FSMContext, lexicon: dict):
        try:
            await message.delete()
        except Exception:
            pass

        await state.clear()
        await state.set_state(GeneralRegistration.choosing_language)
        await message.answer(
            text=lexicon['ru']['welcome'],
            reply_markup=get_language_keyboard()
        )
    @dp.message(Command("menu"))
    async def cmd_menu(message: types.Message, state: FSMContext, lexicon: dict):
        """
        Обработчик команды /menu.
        Принудительно возвращает в главное меню.
        """
        await message.delete()
        user_data = await state.get_data()
        lang = user_data.get('language', 'ru')
        role = user_data.get('role')
        if menu_msg_id := user_data.get('main_menu_message_id'):
            try:
                await bot.delete_message(message.chat.id, menu_msg_id)
            except Exception:
                pass
        is_parent = role == 'parent'

        menu_message = await message.answer(
            text=lexicon[lang]['main-menu-welcome'],
            reply_markup=get_parent_main_menu_keyboard(lexicon, lang) if is_parent else get_student_main_menu_keyboard(lexicon, lang)
        )
        await state.update_data(main_menu_message_id=menu_message.message_id)

    @dp.callback_query(GeneralRegistration.choosing_language, F.data.startswith("lang_"))
    async def language_selected(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
        lang_code = callback.data.split("_")[1]
        await state.update_data(language=lang_code)
        await state.set_state(GeneralRegistration.choosing_role)
        await callback.message.edit_text(
            text=lexicon[lang_code]['choose-role'],
            reply_markup=get_role_keyboard(lexicon=lexicon, lang=lang_code)
        )
        await callback.answer()

    @dp.callback_query(GeneralRegistration.choosing_role, F.data == "back_to_lang_select")
    async def back_to_language(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
        await state.set_state(GeneralRegistration.choosing_language)
        await callback.message.edit_text(
            text=lexicon['ru']['welcome'],
            reply_markup=get_language_keyboard()
        )
        await callback.answer()

    @dp.callback_query(GeneralRegistration.choosing_role, F.data.startswith("role_"))
    async def role_selected(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
        user_data = await state.get_data()
        lang = user_data.get('language', 'ru')
        role = callback.data.split("_")[1]
        await state.update_data(role=role)

        if role == "parent":
            await state.set_state(ParentRegistration.confirming_creation)
            text = (f"{lexicon[lang]['parent-welcome-greeting']}\n\n"
                    f"{lexicon[lang]['parent-welcome-features']}\n\n"
                    f"{lexicon[lang]['parent-welcome-prompt']}")
            await callback.message.edit_text(
                text=text,
                reply_markup=get_profile_creation_keyboard(lexicon=lexicon, lang=lang)
            )

        elif role == "student":
          
            await state.set_state(StudentRegistration.confirming_creation) 
            text = (f"{lexicon[lang]['student-welcome-greeting']}\n\n"
                    f"{lexicon[lang]['student-welcome-features']}\n\n"
                    f"{lexicon[lang]['student-welcome-prompt']}")
            await callback.message.edit_text(
                text=text,
                reply_markup=get_student_welcome_keyboard(lexicon=lexicon, lang=lang)
            )
    dp.include_router(student_router_module.router)
    dp.include_router(parent_router_module.router)
    dp.include_router(parent_actions_router_module.router)
    dp.include_router(programs_router_module.router)
    dp.include_router(universities_router_module.router)
    dp.include_router(profile_router_module.router)
    dp.include_router(stem_navigator_router_module.router)
    dp.include_router(support_router_module.router)
    dp.include_router(professions_router_module.router)
    dp.include_router(main_menu_router_module.router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)

