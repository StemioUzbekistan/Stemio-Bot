import re
import uuid
from datetime import datetime
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from app.utils.google_sheets import RegistrationGSheet
from app.utils.helpers import calculate_age
from app.utils.exode_api import find_user_by_phone, upsert_user
from app.keyboards.reply import get_share_phone_keyboard, get_parent_main_menu_keyboard
from app.keyboards.inline import (
    get_skip_keyboard, get_profile_confirmation_keyboard, get_edit_profile_keyboard,
    get_add_child_keyboard, get_interests_keyboard,
    get_child_confirmation_keyboard, get_city_keyboard,
    get_calendar_with_manual_input_keyboard, get_profile_creation_keyboard,
    get_yes_no_keyboard, get_consent_keyboard
)
from app.states.registration import (
    ParentRegistration,
    ChildRegistration
)

router = Router()
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# --- ХЕЛПЕРЫ ДЛЯ УПРАВЛЕНИЯ ИСТОРИЕЙ СООБЩЕНИЙ ---

async def clear_history(chat_id: int, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    message_ids = user_data.get('message_ids_to_delete', [])
    for msg_id in reversed(message_ids):
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass 
    await state.update_data(message_ids_to_delete=[])

async def append_message_ids(state: FSMContext, *messages: types.Message):
    user_data = await state.get_data()
    ids = user_data.get('message_ids_to_delete', [])
    for msg in messages:
        if msg:
            ids.append(msg.message_id)
    await state.update_data(message_ids_to_delete=ids)

# --- РЕГИСТРАЦИЯ РОДИТЕЛЯ ---

@router.callback_query(ParentRegistration.confirming_creation, F.data == "create_profile")
async def start_parent_registration(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.update_data(message_ids_to_delete=[callback.message.message_id])
    await state.set_state(ParentRegistration.entering_first_name)
    await callback.message.edit_text(lexicon[lang]['prompt-enter-first-name'])
    await callback.answer()

@router.callback_query(ParentRegistration.confirming_creation, F.data == "postpone_creation")
async def postpone_parent_creation_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """
    Обрабатывает нажатие 'Позже' на экране "Создать профиль?" (для родителя)
    """
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    await state.set_state(None) 
    
    menu_message = await callback.message.answer(
        text=lexicon[lang]['main-menu-welcome'], 
        reply_markup=get_parent_main_menu_keyboard(lexicon, lang) 
    )
    await state.update_data(main_menu_message_id=menu_message.message_id)
    await callback.answer()

@router.message(ParentRegistration.entering_first_name)
async def parent_first_name_handler(message: Message, state: FSMContext, lexicon: dict):
    await state.update_data(parent_first_name=message.text.strip())
    user_data = await state.get_data()
    lang = user_data.get('language')

    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_parent_confirmation_screen(message, state, lexicon, message.bot)
    else: 
        await state.set_state(ParentRegistration.entering_last_name)
        next_msg = await message.answer(lexicon[lang]['prompt-enter-last-name'])
        await append_message_ids(state, message, next_msg)

@router.message(ParentRegistration.entering_last_name)
async def parent_last_name_handler(message: Message, state: FSMContext, lexicon: dict):
    await state.update_data(parent_last_name=message.text.strip())
    user_data = await state.get_data()
    lang = user_data.get('language')
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_parent_confirmation_screen(message, state, lexicon, message.bot)
    else:
        await state.set_state(ParentRegistration.entering_phone)
        next_msg = await message.answer(lexicon[lang]['parent-enter-phone-prompt'], reply_markup=get_share_phone_keyboard(lexicon, lang))
        await append_message_ids(state, message, next_msg)

@router.message(ParentRegistration.entering_phone, (F.text | F.contact))
async def parent_phone_handler(message: Message, state: FSMContext, lexicon: dict):
    phone_number = message.text or message.contact.phone_number
    await state.update_data(parent_phone=phone_number)
    user_data = await state.get_data()
    lang = user_data.get('language')
    await message.answer("Спасибо!", reply_markup=ReplyKeyboardRemove())
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_parent_confirmation_screen(message, state, lexicon, message.bot)
    else:
        await state.set_state(ParentRegistration.entering_email)
        next_msg = await message.answer(lexicon[lang]['parent-enter-email-prompt'], reply_markup=get_skip_keyboard(lexicon, lang))
        await append_message_ids(state, message, next_msg)

@router.message(ParentRegistration.entering_email)
async def parent_email_handler(message: Message, state: FSMContext, lexicon: dict):
    email = message.text.strip()
    user_data = await state.get_data()
    lang = user_data.get('language')
    if email and not re.match(EMAIL_REGEX, email):
        error_msg = await message.answer(lexicon[lang]['parent-email-error'], reply_markup=get_skip_keyboard(lexicon, lang))
        
        await append_message_ids(state, message, error_msg)
        return
        
    await state.update_data(parent_email=email if email else "Пропущено")
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_parent_confirmation_screen(message, state, lexicon, message.bot)
    else:
        await show_parent_confirmation_screen(message, state, lexicon, message.bot)

@router.callback_query(ParentRegistration.entering_email, F.data == "skip_email")
async def skip_email_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await state.update_data(parent_email="Пропущено")
    await show_parent_confirmation_screen(callback.message, state, lexicon, callback.bot)
    await callback.answer()

# --- ЭКРАНЫ ПОДТВЕРЖДЕНИЯ ---

async def show_parent_confirmation_screen(message: types.Message | types.CallbackQuery, state: FSMContext, lexicon: dict, bot: Bot):
    await clear_history(message.chat.id if isinstance(message, types.Message) else message.message.chat.id, state, bot)
    user_data = await state.get_data()
    lang = user_data.get('language')
    confirmation_text = lexicon[lang]['parent-profile-confirmation'].format(
        first_name=user_data.get('parent_first_name'),
        last_name=user_data.get('parent_last_name'),
        phone=user_data.get('parent_phone'),
        email=user_data.get('parent_email')
    )
    target_message = message if isinstance(message, types.Message) else message.message
    if isinstance(message, types.CallbackQuery):
        try:
            await message.message.delete()
        except Exception:
            pass 
            
    conf_msg = await target_message.answer(confirmation_text, reply_markup=get_profile_confirmation_keyboard(lexicon, lang))
    await state.update_data(message_ids_to_delete=[conf_msg.message_id])
    await state.set_state(ParentRegistration.confirming_profile)


# --- ПОДТВЕРЖДЕНИЕ И СОХРАНЕНИЕ ПРОФИЛЯ РОДИТЕЛЯ ---

@router.callback_query(ParentRegistration.confirming_profile, F.data == "confirm_profile")
async def confirm_parent_profile_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    """Подтверждение и сохранение профиля родителя с созданием аккаунта в Exode."""
    await clear_history(callback.message.chat.id, state, callback.bot)
    await state.update_data(telegram_id=callback.from_user.id)
    user_data = await state.get_data()
    lang = user_data.get('language')
    registration_manager.add_parent(user_data)
    payload = {
        'tgId': callback.from_user.id,
        'profile': {
            'firstName': user_data.get('parent_first_name'),
            'lastName': user_data.get('parent_last_name'),
            'role': 'Parent'
        }
    }

    if user_data.get('parent_phone'):
        phone = user_data['parent_phone']
        if not phone.startswith('+'):
            phone = '+' + phone
        payload['phone'] = phone

    if user_data.get('parent_email') and user_data.get('parent_email') != 'Пропущено':
        payload['email'] = user_data['parent_email']

    exode_result = upsert_user(payload)
    if not exode_result:
        print("Warning: Failed to create Exode account for parent")

    await state.set_state(ParentRegistration.adding_child_decision)
    
    success_text = lexicon[lang].get('profile-confirmed', "Спасибо, ваш профиль создан!")
    
    next_msg = await callback.message.answer(
        success_text + "\n\n" + lexicon[lang]['add-child-prompt'],
        reply_markup=get_add_child_keyboard(lexicon, lang)
    )
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(ParentRegistration.confirming_profile, F.data == "edit_profile")
async def edit_parent_profile_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.set_state(ParentRegistration.editing_profile)
    await callback.message.edit_text(
        lexicon[lang]['choose-field-to-edit'],
        reply_markup=get_edit_profile_keyboard(lexicon, lang)
    )
    await callback.answer()

@router.callback_query(ParentRegistration.editing_profile, F.data.startswith("edit_"))
async def edit_field_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    field = callback.data.replace("edit_", "")
    await state.update_data(editing_during_registration=True)
    
    prompts = { "Имя": lexicon[lang]['prompt-enter-first-name'], "Фамилия": lexicon[lang]['prompt-enter-last-name'], "Номер телефона": lexicon[lang]['parent-enter-phone-prompt'], "Email": lexicon[lang]['parent-enter-email-prompt'] }
    target_states = { "Имя": ParentRegistration.entering_first_name, "Фамилия": ParentRegistration.entering_last_name, "Номер телефона": ParentRegistration.entering_phone, "Email": ParentRegistration.entering_email }
    
    target_state = target_states.get(field)
    prompt_text = prompts.get(field)
    if not target_state or not prompt_text:
        await callback.answer("Ошибка: Неизвестное поле.", show_alert=True)
        return

    await state.set_state(target_state)
    await callback.message.delete() 
    next_msg = await callback.message.answer(prompt_text, reply_markup=get_share_phone_keyboard(lexicon, lang) if field == 'Номер телефона' else (get_skip_keyboard(lexicon, lang) if field == 'Email' else None))
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(ParentRegistration.editing_profile, F.data == "back_to_confirmation")
async def back_to_confirmation_from_edit(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await show_parent_confirmation_screen(callback.message, state, lexicon, callback.bot)
    await callback.answer()

# --- ОБРАБОТЧИКИ КНОПОК "НАЗАД" ---
@router.callback_query(ParentRegistration.entering_email, F.data == "back_to_phone_input")
async def back_to_phone_input_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(ParentRegistration.entering_phone)
    next_msg = await callback.message.answer(lexicon[lang]['parent-enter-phone-prompt'], reply_markup=get_share_phone_keyboard(lexicon, lang))
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(ParentRegistration.confirming_profile, F.data == "back_to_email_input")
async def back_to_email_input_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.set_state(ParentRegistration.entering_email)
    next_msg = await callback.message.answer(lexicon[lang]['parent-enter-email-prompt'], reply_markup=get_skip_keyboard(lexicon, lang))
    await state.update_data(message_ids_to_delete=[next_msg.message_id]) 
    await callback.answer()

@router.callback_query(ParentRegistration.adding_child_decision, F.data == "back_to_profile_confirmation")
async def back_to_profile_confirmation_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await show_parent_confirmation_screen(callback.message, state, lexicon, callback.bot)
    await callback.answer()

@router.callback_query(ChildRegistration.confirming_child, F.data == "back_to_interests")
async def back_to_interests_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    user_data = await state.get_data()
    chosen_interests = user_data.get('child_interests', set())
    await state.set_state(ChildRegistration.choosing_interests)
    await callback.message.edit_text(
        lexicon[lang]['child-choose-interests-prompt'],
        reply_markup=get_interests_keyboard(lexicon, lang, chosen_interests)
    )
    await callback.answer()

# --- ДОБАВЛЕНИЕ РЕБЕНКА (СУЩЕСТВУЮЩЕГО) ---

@router.callback_query(ParentRegistration.adding_child_decision, F.data == "add_child")
async def add_child_start(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """Шаг 1: Спрашиваем, зарегистрирован ли ребенок."""
    lang = (await state.get_data()).get('language')
    await state.set_state(ParentRegistration.asking_child_registered)
    await callback.message.edit_text(lexicon[lang]['is-child-registered-prompt'], reply_markup=get_yes_no_keyboard(lexicon, lang))
    await callback.answer()

@router.callback_query(ParentRegistration.asking_child_registered)
async def process_existing_child_prompt(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """Шаг 2: Обрабатываем ответ 'Да' или 'Нет'."""
    lang = (await state.get_data()).get('language')

    if callback.data == 'yes':
        await state.set_state(ParentRegistration.entering_child_phone)
        await callback.message.edit_text(lexicon[lang]['enter-child-phone-prompt'])
    else:
        await state.set_state(ChildRegistration.entering_first_name)
        await callback.message.edit_text(lexicon[lang]['child-enter-name-prompt'])
    
    await callback.answer()

@router.message(ParentRegistration.entering_child_phone)
async def process_child_phone_number(message: Message, state: FSMContext, lexicon: dict):
    """Шаг 3: Ищем ребенка по номеру телефона в Exode."""
    phone_number = message.text.strip()

    await state.update_data(temp_child_phone=phone_number) 

    lang = (await state.get_data()).get('language')
    searching_msg = await message.answer(lexicon[lang]['searching-user'])
    await append_message_ids(state, message, searching_msg) 
    child_data = find_user_by_phone(phone_number)
    full_name = ""
    
    if child_data:
        await state.update_data(found_child_payload=child_data) 
        
        user_obj = child_data.get('user', {})
        profile_obj = child_data.get('profile', {})
        
        if profile_obj and profile_obj.get('firstName'):
            full_name = f"{profile_obj.get('firstName', '')} {profile_obj.get('lastName', '')}".strip()

    if full_name:
        confirmation_text = lexicon[lang]['found-child-confirmation'].format(
            first_name=profile_obj.get('firstName', ''), 
            last_name=profile_obj.get('lastName', '')
        )
    elif child_data:
        confirmation_text = lexicon[lang]['child-found-no-name'].format(phone=phone_number)
    else:
        confirmation_text = lexicon[lang]['child-not-found-prompt']

    await state.set_state(ParentRegistration.confirming_found_child)
    await searching_msg.delete()
    
    builder = InlineKeyboardBuilder()
    if child_data:
        builder.row(types.InlineKeyboardButton(
            text=lexicon[lang]['button-this-is-my-child'],
            callback_data="confirm_found_child_yes"
        ))
        builder.row(types.InlineKeyboardButton(
            text=lexicon[lang]['button-add-another'], 
            callback_data="confirm_found_child_no"
        ))
    else:
        builder.row(types.InlineKeyboardButton(
            text=lexicon[lang]['button-add-child'], 
            callback_data="confirm_found_child_no" 
        ))

    await message.answer(confirmation_text, reply_markup=builder.as_markup())

@router.callback_query(ParentRegistration.confirming_found_child)
async def process_found_child_confirmation(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    """
    Шаг 4: Обрабатываем подтверждение найденного ребенка.
    """
    user_data = await state.get_data()
    lang = user_data.get('language')
    found_child_payload = user_data.get('found_child_payload') 

    if callback.data == 'confirm_found_child_yes' and found_child_payload:
        user_obj = found_child_payload.get('user') or {}
        
        exode_id = user_obj.get('id')
        if not exode_id:
            await callback.message.edit_text(lexicon[lang]['api-error-prompt'])
            return
        await state.update_data(
            exode_user_id=exode_id,
            child_phone=user_obj.get('phone', user_data.get('temp_child_phone', '')) 
        )
        await state.set_state(ChildRegistration.entering_first_name)
        await callback.message.edit_text(lexicon[lang]['child-enter-name-prompt'])

    else:
        await state.set_state(ChildRegistration.entering_first_name)
        await callback.message.edit_text(lexicon[lang]['child-enter-name-prompt'])
    
    await callback.answer()

# --- ГЛАВНОЕ МЕНЮ И ЗАВЕРШЕНИЕ ---

@router.callback_query(ParentRegistration.adding_child_decision, F.data == "no_child")
async def finish_parent_registration(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """Завершаем регистрацию и показываем главное меню."""
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(None) 
    await state.update_data(role='parent')
    
    menu_message = await callback.message.answer(
        lexicon[lang]['main-menu-welcome'],
        reply_markup=get_parent_main_menu_keyboard(lexicon, lang)
    )
    await state.update_data(main_menu_message_id=menu_message.message_id) 
    await callback.answer()

# --- ДОБАВЛЕНИЕ НОВОГО РЕБЕНКА ---
@router.message(ChildRegistration.entering_first_name)
async def child_first_name_handler(message: Message, state: FSMContext, lexicon: dict):
    await state.update_data(child_first_name=message.text.strip())
    lang = (await state.get_data()).get('language')
    await state.set_state(ChildRegistration.entering_last_name)
    
    next_msg = await message.answer(lexicon[lang].get('prompt-enter-last-name', 'Напишите фамилию ребенка:'))
    await append_message_ids(state, message, next_msg)

@router.message(ChildRegistration.entering_last_name)
async def child_last_name_handler(message: Message, state: FSMContext, lexicon: dict):
    await state.update_data(child_last_name=message.text.strip())
    lang = (await state.get_data()).get('language')
    await state.set_state(ChildRegistration.entering_dob)
    next_msg = await message.answer(lexicon[lang]['child-enter-dob-prompt'], reply_markup=await get_calendar_with_manual_input_keyboard(lexicon, lang))
    await append_message_ids(state, message, next_msg)
@router.callback_query(ChildRegistration.entering_dob, SimpleCalendarCallback.filter())
async def process_child_calendar_selection(callback: types.CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await state.update_data(child_dob=date.strftime("%d.%m.%Y"))
        await state.set_state(ChildRegistration.entering_class)
        await callback.message.edit_text(lexicon[lang]['child-enter-class-prompt'])
    await callback.answer()

@router.callback_query(ChildRegistration.entering_dob, F.data == "manual_dob_input")
async def manual_child_dob_input_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.set_state(ChildRegistration.entering_dob_manually)
    
    await callback.message.edit_text(lexicon[lang].get('child-enter-dob-prompt', 'Введите дату в формате ДД.ММ.ГГГГ:'))
    await callback.answer()

@router.message(ChildRegistration.entering_dob_manually)
async def process_manual_child_dob_input(message: Message, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    try:
        datetime.strptime(message.text, '%d.%m.%Y')
        await state.update_data(child_dob=message.text)
        await state.set_state(ChildRegistration.entering_class)
        next_msg = await message.answer(lexicon[lang]['child-enter-class-prompt'])
        await append_message_ids(state, message, next_msg)
    except ValueError:
        error_msg = await message.answer(lexicon[lang]['child-enter-dob-error']) # (В texts.json 'child-dob-error')
        await append_message_ids(state, message, error_msg)

@router.message(ChildRegistration.entering_class)
async def child_class_handler(message: Message, state: FSMContext, lexicon: dict):
    class_text = message.text.strip()
    lang = (await state.get_data()).get('language')
    if not class_text.isdigit() or not (1 <= int(class_text) <= 11):
        await message.answer(lexicon[lang]['class-input-error'])
        return 
        
    await state.update_data(child_class=class_text)
    await state.set_state(ChildRegistration.entering_city)
    next_msg = await message.answer(lexicon[lang]['child-enter-city-prompt'], reply_markup=get_city_keyboard(lang))
    await append_message_ids(state, message, next_msg)

@router.callback_query(ChildRegistration.entering_city, F.data.startswith("city_") | (F.data == "manual_city_input"))
async def child_city_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    if callback.data == "manual_city_input":
        await state.set_state(ChildRegistration.entering_city_manually)
        await callback.message.edit_text("Пожалуйста, напишите название вашего города:")
        await callback.answer()
        return
    city = callback.data.split("_", 1)[1]
    await state.update_data(child_city=city)
    await state.set_state(ChildRegistration.choosing_interests)
    await callback.message.edit_text(lexicon[lang]['child-choose-interests-prompt'], reply_markup=get_interests_keyboard(lexicon, lang, set()))
    await callback.answer()

@router.message(ChildRegistration.entering_city_manually)
async def process_manual_child_city_input(message: Message, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.update_data(child_city=message.text.strip())
    await state.set_state(ChildRegistration.choosing_interests)
    next_msg = await message.answer(lexicon[lang]['child-choose-interests-prompt'], reply_markup=get_interests_keyboard(lexicon, lang, set()))
    await append_message_ids(state, message, next_msg)

@router.callback_query(ChildRegistration.choosing_interests, F.data.startswith("interest_"))
async def toggle_interest_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    interest_key = callback.data.split("_")[1]
    user_data = await state.get_data()
    lang = user_data.get('language')
    chosen_interests = set(user_data.get('child_interests', []))
    if interest_key in chosen_interests:
        chosen_interests.remove(interest_key)
    else:
        chosen_interests.add(interest_key)
    await state.update_data(child_interests=list(chosen_interests))
    await callback.message.edit_reply_markup(reply_markup=get_interests_keyboard(lexicon, lang, chosen_interests))
    await callback.answer()

@router.callback_query(ChildRegistration.choosing_interests, F.data == "interests_done")
async def interests_done_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await callback.message.delete()
    
    user_data = await state.get_data()
    lang = user_data.get('language')
    dob = user_data.get('child_dob')
    age = calculate_age(dob)
    interests_keys = user_data.get('child_interests', [])
    interests_text = ", ".join([lexicon[lang].get(f'button-{key}', key) for key in interests_keys]) if interests_keys else lexicon[lang]['not-specified']
    
    confirmation_text = lexicon[lang]['child-profile-confirmation'].format(
        first_name=user_data.get('child_first_name'),
        last_name=user_data.get('child_last_name'),
        dob=dob, age=age,
        class_level=user_data.get('child_class'),
        city=user_data.get('child_city'),
        interests=interests_text
    )
    conf_msg = await callback.message.answer(confirmation_text, reply_markup=get_child_confirmation_keyboard(lexicon, lang))
    await state.update_data(message_ids_to_delete=[conf_msg.message_id])
    await state.set_state(ChildRegistration.confirming_child)
    await callback.answer()

@router.callback_query(ChildRegistration.confirming_child, F.data == "confirm_child")
async def confirm_child_and_ask_consent_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    await clear_history(callback.message.chat.id, state, callback.bot)
    
    user_data = await state.get_data()
    lang = user_data.get('language')
    registration_manager.add_child(parent_id=callback.from_user.id, data=user_data)
    if user_data.get('exode_user_id'):       
        message_text = lexicon[lang]['child-profile-linked-success']
        await state.update_data(
            child_first_name=None, child_last_name=None, child_dob=None,
            child_class=None, child_city=None, child_interests=None,
            found_child_payload=None, temp_child_phone=None,
            exode_user_id=None, child_phone=None
        )
        
        next_msg = await callback.message.answer(
            message_text + "\n\n" + lexicon[lang]['add-another-child-prompt'],
            reply_markup=get_add_child_keyboard(lexicon, lang)
        )
        await state.update_data(message_ids_to_delete=[next_msg.message_id])
        await state.set_state(ParentRegistration.adding_child_decision)

    else:
        next_msg = await callback.message.answer(lexicon[lang]['platform-consent-prompt'], reply_markup=get_consent_keyboard(lexicon, lang))
        await state.update_data(message_ids_to_delete=[next_msg.message_id])
        await state.set_state(ChildRegistration.confirming_exode_creation)

    await callback.answer()

@router.callback_query(ChildRegistration.confirming_exode_creation)
async def finalize_child_registration_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """Обработчик согласия на создание аккаунта в Exode для ребенка."""
    await clear_history(callback.message.chat.id, state, callback.bot)

    user_data = await state.get_data()
    lang = user_data.get('language')
    message_text = ""

    if callback.data == "consent_yes":
        payload = {
            'profile': {
                'firstName': user_data.get('child_first_name'),
                'lastName': user_data.get('child_last_name'),
                'bdate': datetime.strptime(user_data.get('child_dob'), '%d.%m.%Y').strftime('%Y-%m-%d'),
                'role': 'Student'
            }
        }
        
        if user_data.get('parent_phone'):
            phone = user_data['parent_phone']
            if not phone.startswith('+'):
                phone = '+' + phone
            payload['phone'] = phone
        elif user_data.get('parent_email') and user_data.get('parent_email') != 'Пропущено':
            payload['email'] = user_data['parent_email']
        else: 
            unique_id = str(uuid.uuid4())[:8]
            payload['email'] = f"child_{unique_id}@school.local"
        new_exode_user = upsert_user(payload)
        
        if new_exode_user and new_exode_user.get('user'):
            message_text = lexicon[lang]['child-profile-created-success']
        else:
            message_text = lexicon[lang]['api-error-prompt']
            
    elif callback.data == "consent_no":
        message_text = lexicon[lang]['child-profile-created-locally']

    await state.update_data(
        child_first_name=None,
        child_last_name=None,
        child_dob=None,
        child_class=None,
        child_city=None,
        child_interests=None,
        found_child_payload=None, 
        temp_child_phone=None,
        exode_user_id=None,
        child_phone=None
    )
    
    next_msg = await callback.message.answer(
        message_text + "\n\n" + lexicon[lang]['add-another-child-prompt'],
        reply_markup=get_add_child_keyboard(lexicon, lang)
    )
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await state.set_state(ParentRegistration.adding_child_decision)
    await callback.answer()

@router.callback_query(ParentRegistration.adding_child_decision, F.data == "finish_registration")
async def finish_parent_registration_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    from app.keyboards.reply import get_parent_main_menu_keyboard
    await state.set_state(None) 
    
    menu_message = await callback.message.answer(
        text=lexicon[lang].get('main-menu-welcome', 'Добро пожаловать в главное меню!'),
        reply_markup=get_parent_main_menu_keyboard(lexicon, lang)
    )
    await state.update_data(main_menu_message_id=menu_message.message_id)
    await callback.answer()

