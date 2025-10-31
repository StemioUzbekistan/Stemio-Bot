# app/handlers/profile.py

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- 1. ИСПРАВЛЕННЫЕ ИМПОРТЫ ---
from app.utils.google_sheets import RegistrationGSheet 
from app.states.registration import ProfileEditing, GeneralRegistration, ParentRegistration, StudentRegistration
from app.keyboards.inline import (
    get_profile_keyboard, get_edit_profile_choices_keyboard,
    get_children_list_keyboard, get_back_to_children_list_keyboard,
    get_language_keyboard, get_yes_no_keyboard,
    get_student_welcome_keyboard, get_profile_creation_keyboard 
)
from app.utils.helpers import calculate_age

router = Router()


# --- ГЛАВНЫЙ ОБРАБОТЧИК ПРОФИЛЯ ---

@router.message(F.text.in_({"👤 Профиль", "⚙️ Профиль", "👤 Profil"}))
async def profile_handler(message: types.Message, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    await message.delete()
    
    # --- Логика удаления сообщения главного меню ---
    user_fsm_data = await state.get_data() # Переименовал, чтобы не путать
    if menu_msg_id := user_fsm_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass
    # --- Конец логики ---
    
    lang = user_fsm_data.get('language', 'ru') # Используем уже сохраненный lang
    user_data = registration_manager.get_user_by_id(message.from_user.id)

    if user_data:
        # Если профиль НАЙДЕН в Google-таблице
        await state.set_state(ProfileEditing.showing_profile)
        await show_profile_screen(message, state, lexicon, lang, user_data, registration_manager)
    else:
        # --- (Если профиль НЕ найден) ---
        
        role = user_fsm_data.get('role') # Получаем роль, сохраненную после "Позже"

        # Текст, который вы хотите
        text = "Кажется, у вас еще нет профиля. Давайте создадим его!"
        
        # Проверяем, какая роль была выбрана
        if role == 'student':
            # Кнопки "Да, давай" и "Позже"
            await state.set_state(StudentRegistration.confirming_creation)
            await message.answer(
                text=text,
                reply_markup=get_student_welcome_keyboard(lexicon=lexicon, lang=lang)
            )
        elif role == 'parent':
             # На случай, если родитель нажмет "Позже"
            await state.set_state(ParentRegistration.confirming_creation)
            await message.answer(
                text=text, 
                reply_markup=get_profile_creation_keyboard(lexicon=lexicon, lang=lang)
            )
        else:
            # Если роли нет (пользователь не нажимал /start), начинаем с языка
            await state.set_state(GeneralRegistration.choosing_language)
            await message.answer(
                text="Кажется, у вас еще нет профиля. Давайте создадим его! Выберите язык:",
                reply_markup=get_language_keyboard()
            )


# --- ОБРАБОТЧИК "МОИ ДЕТИ"  ---
@router.message(F.text.in_({"👤 Мои дети", "👤 Mening farzandlarim"}))
async def my_children_handler(message: types.Message, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    await message.delete()
    
    # --- Логика удаления сообщения главного меню ---
    user_fsm_data = await state.get_data()
    if menu_msg_id := user_fsm_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass
    # --- Конец логики ---

    lang = user_fsm_data.get('language', 'ru')
    
    # 1. Проверяем, зарегистрирован ли родитель
    user_data = registration_manager.get_user_by_id(message.from_user.id)
    if not (user_data and user_data.get('role') == 'parent'):

        role = user_fsm_data.get('role')
        text = "Кажется, у вас еще нет профиля. Давайте создадим его!"
        
        if role == 'parent':
            await state.set_state(ParentRegistration.confirming_creation)
            await message.answer(
                text=text, 
                reply_markup=get_profile_creation_keyboard(lexicon=lexicon, lang=lang)
            )
        else:
             await state.set_state(GeneralRegistration.choosing_language)
             await message.answer(
                text="Кажется, у вас еще нет профиля родителя. Давайте создадим его! Выберите язык:",
                reply_markup=get_language_keyboard()
             )
        return

    # 2. Пользователь - родитель. Показываем список детей.
    await state.set_state(ProfileEditing.managing_children)
    
    # --- Эта логика скопирована из `show_children_list` и адаптирована ---
    children = registration_manager.get_children_by_parent_id(message.from_user.id)
    
    if children:
        # Отправляем НОВОЕ сообщение
        await message.answer(
            lexicon[lang]['my-children-list-title'],
            reply_markup=get_children_list_keyboard(children, lexicon, lang)
        )
    else:
        # Показываем кнопки "Добавить" и "Назад" (в ГЛАВНОЕ МЕНЮ)
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(
            text=lexicon[lang].get('button-add-child', 'Добавить ребенка'),
            callback_data="add_child_from_profile"
        ))

        builder.row(types.InlineKeyboardButton(
            text=lexicon[lang]['button-back'],
            callback_data="back_to_main_menu"
        ))
        await message.answer(
            "У вас пока нет добавленных детей.",
            reply_markup=builder.as_markup()
        )


# --- ХЕЛПЕРЫ ДЛЯ ОТОБРАЖЕНИЯ ---

async def show_profile_screen(
    message: types.Message | types.CallbackQuery, 
    state: FSMContext, 
    lexicon: dict, 
    lang: str, 
    user_data: dict, 
    registration_manager: RegistrationGSheet
):

    target_message = message if isinstance(message, types.Message) else message.message
    bot = message.bot

    if isinstance(message, types.CallbackQuery):
        # Если это callback, мы редактируем сообщение
        target_message = message.message
    else:
        # Если это message (от /profile), мы отправляем новое
        target_message = message
        # И удаляем старое (команду /profile)
        try: await message.delete()
        except: pass
    

    async def send_or_edit(text, reply_markup, parse_mode):
        try:
            await target_message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except:
            await bot.send_message(target_message.chat.id, text, reply_markup=reply_markup, parse_mode=parse_mode)

            
    user_role = user_data.get('role')

    if user_role == 'parent':
        text = lexicon[lang]['profile-parent-display'].format(
            first_name=user_data.get('Имя'),
            last_name=user_data.get('Фамилия'),
            phone=user_data.get('Номер телефона'),
            email=user_data.get('Email') or "Не указан"
        )
        keyboard = get_profile_keyboard(lexicon, lang, is_parent=True)
        await send_or_edit(text, reply_markup=keyboard, parse_mode="Markdown")
    
    elif user_role == 'student':
        parent_contact = registration_manager.get_student_parent_contact(user_data.get('Telegram ID'))
        age = calculate_age(user_data.get('Дата рождения'))
        text = lexicon[lang]['profile-student-display'].format(
            first_name=user_data.get('Имя'),
            last_name=user_data.get('Фамилия'),
            dob=user_data.get('Дата рождения'), age=age or 'N/A', 
            phone=user_data.get('Телефон') or "Не указан",
            city=user_data.get('Город'), 
            parent_contact=parent_contact or "Не указан"
        )
        keyboard = get_profile_keyboard(lexicon, lang, is_parent=False)
        await send_or_edit(text, reply_markup=keyboard, parse_mode="Markdown")
        
    else:
        await target_message.answer("Не удалось определить вашу роль. Пожалуйста, пройдите регистрацию заново, написав /start")

async def show_children_list(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, lang: str, registration_manager: RegistrationGSheet):

    children = registration_manager.get_children_by_parent_id(callback.from_user.id)
    
    if children:
        await callback.message.edit_text(
            lexicon[lang]['my-children-list-title'],
            reply_markup=get_children_list_keyboard(children, lexicon, lang)
        )
    else:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(
            text=lexicon[lang].get('button-add-child', 'Добавить ребенка'),
            callback_data="add_child_from_profile"
        ))
        # Эта кнопка "Назад" - правильная, она ведет в "Профиль"
        builder.row(types.InlineKeyboardButton(
            text=lexicon[lang]['button-back'],
            callback_data="back_to_profile_view" 
        ))
        await callback.message.edit_text(
            "У вас пока нет добавленных детей.",
            reply_markup=builder.as_markup()
        )

# --- УПРАВЛЕНИЕ ДЕТЬМИ (ДЛЯ РОДИТЕЛЯ) ---

@router.callback_query(ProfileEditing.showing_profile, F.data == "manage_children_action")
async def manage_children_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(ProfileEditing.managing_children)
    await show_children_list(callback, state, lexicon, lang, registration_manager)
    await callback.answer()

@router.callback_query(ProfileEditing.managing_children, F.data.startswith("view_child_"))
async def view_child_details_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    try:
        child_index = int(callback.data.split("_")[2])
        lang = (await state.get_data()).get('language', 'ru')
        
        children = registration_manager.get_children_by_parent_id(callback.from_user.id)
        child = children[child_index]

        if child:
            age = calculate_age(child.get('Дата рождения'))
            child_name = f"{child.get('Имя ребенка', '')} {child.get('Фамилия ребенка', '')}".strip()
            
            text = lexicon[lang]['child-details-display'].format(
                first_name=child.get('Имя ребенка', ''), 
                last_name=child.get('Фамилия ребенка', ''),
                dob=child.get('Дата рождения', 'не указана'), age=age or 'N/A', 
                city=child.get('Город', 'не указан'), interests=child.get('Интересы', 'не указаны'), 
                courses="Пока не записан на курсы"
            )
            await state.set_state(ProfileEditing.viewing_child_details)
            await callback.message.edit_text(text, reply_markup=get_back_to_children_list_keyboard(lexicon, lang))
    except (ValueError, IndexError):
        await callback.answer("Не удалось найти информацию о ребенке. Попробуйте снова.", show_alert=True)
    await callback.answer()

@router.callback_query(ProfileEditing.viewing_child_details, F.data == "back_to_children_list")
async def back_to_children_list_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(ProfileEditing.managing_children)
    await show_children_list(callback, state, lexicon, lang, registration_manager)
    await callback.answer()

@router.callback_query(ProfileEditing.managing_children, F.data == "add_child_from_profile")
async def add_child_from_profile_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(ParentRegistration.asking_child_registered)
    await callback.message.edit_text(
        lexicon[lang]['is-child-registered-prompt'],
        reply_markup=get_yes_no_keyboard(lexicon, lang)
    )
    await callback.answer()

# --- РЕДАКТИРОВАНИЕ ПРОФИЛЯ ---

@router.callback_query(ProfileEditing.showing_profile, F.data == "edit_profile_action")
async def edit_profile_action_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    user_data = registration_manager.get_user_by_id(callback.from_user.id)
    is_parent = user_data and user_data.get('role') == 'parent'

    await state.set_state(ProfileEditing.choosing_field_to_edit)
    await callback.message.edit_text(
        lexicon[lang]['profile-edit-prompt'],
        reply_markup=get_edit_profile_choices_keyboard(lexicon, lang, is_parent)
    )
    await callback.answer()

@router.callback_query(ProfileEditing.choosing_field_to_edit, F.data.startswith("edit_field_"))
async def edit_field_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    # edit_field_parent_Имя или edit_field_student_Имя
    parts = callback.data.split("_", 3)
    role_prefix = parts[2] # 'parent' или 'student'
    field_to_edit = parts[3] # 'Имя'
    
    await state.set_state(ProfileEditing.editing_field)
    await state.update_data(field_to_edit=field_to_edit, role_prefix_for_edit=role_prefix)
    
    lang = (await state.get_data()).get('language', 'ru')
    prompt_text = lexicon[lang].get('prompt-enter-new-name', "Введите новое значение:") # Запасной текст
    
    # Подбираем правильный текст
    if field_to_edit == "Имя" or field_to_edit == "Фамилия":
        prompt_text = lexicon[lang]['prompt-enter-new-name']
    elif "Телефон" in field_to_edit:
        prompt_text = lexicon[lang]['prompt-enter-new-phone']
    elif field_to_edit == "Email":
        prompt_text = lexicon[lang]['prompt-enter-new-email']
    elif "Дата рождения" in field_to_edit:
         prompt_text = lexicon[lang]['prompt-enter-new-age']
    elif field_to_edit == "Город":
         prompt_text = lexicon[lang]['prompt-enter-new-city']

    await callback.message.edit_text(prompt_text)
    await callback.answer()

@router.message(ProfileEditing.editing_field)
async def save_edited_field_handler(message: types.Message, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    user_data_from_state = await state.get_data()
    field_to_edit = user_data_from_state.get('field_to_edit')
    new_value = message.text.strip()
    
    await message.delete()

    success = registration_manager.update_user_data(
        user_id=message.from_user.id,
        field_name=field_to_edit,
        new_value=new_value
    )
    
    updated_user_data = registration_manager.get_user_by_id(message.from_user.id)

    if success and updated_user_data:
        # Передаем registration_manager дальше
        await show_profile_screen(message, state, lexicon, lang, updated_user_data, registration_manager)
    else:
        await message.answer("Не удалось обновить профиль. Попробуйте снова.")

# --- КНОПКА "НАЗАД" ---

@router.callback_query(F.data == "back_to_profile_view")
async def back_to_profile_view_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    user_data = registration_manager.get_user_by_id(callback.from_user.id)
    if user_data:
        await state.set_state(ProfileEditing.showing_profile)
        # Передаем registration_manager дальше
        await show_profile_screen(callback, state, lexicon, lang, user_data, registration_manager)
    await callback.answer()

@router.callback_query(ProfileEditing.showing_profile, F.data == "my_courses_action")
async def my_courses_stub_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    await callback.answer(lexicon[lang]['coming-soon'], show_alert=True)


