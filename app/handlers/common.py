# from aiogram import Router, F, types
# from aiogram.filters import CommandStart
# from aiogram.fsm.context import FSMContext

# # Импортируем все наши клавиатуры
# from app.keyboards.inline import (
#     get_language_keyboard,
#     get_role_keyboard,
#     get_profile_creation_keyboard,
#     get_student_welcome_keyboard
# )
# # Импортируем все наши состояния
# from app.states.registration import (
#     GeneralRegistration,
#     ParentRegistration,
#     StudentRegistration
# )

# router = Router()

# @router.message(CommandStart())
# async def cmd_start(message: types.Message, state: FSMContext, lexicon: dict):
#     """
#     Обработчик команды /start. Начинает диалог с выбора языка.
#     """
#     # Удаляем предыдущее сообщение, если это возможно, чтобы избежать дублирования
#     try:
#         await message.delete()
#     except Exception:
#         pass # Если сообщение не удалось удалить (например, в группе), просто игнорируем

#     await state.clear() # Очищаем состояние на случай, если пользователь перезапускает бота
#     await state.set_state(GeneralRegistration.choosing_language)
#     await message.answer(
#         text=lexicon['ru']['welcome'], # Стартовое сообщение всегда на русском
#         reply_markup=get_language_keyboard()
#     )

# @router.callback_query(GeneralRegistration.choosing_language, F.data.startswith("lang_"))
# async def language_selected(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
#     """
#     Обрабатывает выбор языка, сохраняет его в состоянии и предлагает выбрать роль.
#     """
#     lang_code = callback.data.split("_")[1]
#     await state.update_data(language=lang_code)
#     await state.set_state(GeneralRegistration.choosing_role)

#     await callback.message.edit_text(
#         text=lexicon[lang_code]['choose-role'],
#         reply_markup=get_role_keyboard(lexicon=lexicon, lang=lang_code)
#     )
#     await callback.answer()

# @router.callback_query(GeneralRegistration.choosing_role, F.data == "back_to_lang_select")
# async def back_to_language(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
#     """
#     Обрабатывает нажатие кнопки "Назад" на этапе выбора роли,
#     возвращая к выбору языка.
#     """
#     await state.set_state(GeneralRegistration.choosing_language)
#     # ИСПРАВЛЕНО: Теперь приветствие всегда будет на русском, что логично для первого шага
#     await callback.message.edit_text(
#         text=lexicon['ru']['welcome'],
#         reply_markup=get_language_keyboard()
#     )
#     await callback.answer()

# @router.callback_query(GeneralRegistration.choosing_role, F.data.startswith("role_"))
# async def role_selected(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
#     """
#     Обрабатывает выбор роли и направляет пользователя по соответствующей ветке регистрации.
#     """
#     user_data = await state.get_data()
#     lang = user_data.get('language', 'ru') # Используем 'ru' как язык по умолчанию
#     role = callback.data.split("_")[1]
    
#     await state.update_data(role=role) # Сохраняем выбранную роль в состоянии

#     if role == "parent":
#         await state.set_state(ParentRegistration.confirming_creation)
#         text = (f"{lexicon[lang]['parent-welcome-greeting']}\n\n"
#                 f"{lexicon[lang]['parent-welcome-features']}\n\n"
#                 f"{lexicon[lang]['parent-welcome-prompt']}")
#         await callback.message.edit_text(
#             text=text,
#             reply_markup=get_profile_creation_keyboard(lexicon=lexicon, lang=lang)
#         )
    
#     elif role == "student":
#         await state.set_state(StudentRegistration.asking_if_registered)
#         text = (f"{lexicon[lang]['student-welcome-greeting']}\n\n"
#                 f"{lexicon[lang]['student-welcome-features']}\n\n"
#                 f"{lexicon[lang]['student-welcome-prompt']}")
#         await callback.message.edit_text(
#             text=text,
#             reply_markup=get_student_welcome_keyboard(lexicon=lexicon, lang=lang)
#         )

#     await callback.answer()