from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, Message
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from datetime import datetime
import logging

from app.utils.exode_api import find_user_by_phone, upsert_user
from app.utils.google_sheets import RegistrationGSheet, CoursesGSheet
from app.states.registration import StudentRegistration, StemNavigator, Programs
from app.keyboards.inline import (
    get_yes_no_keyboard, 
    get_consent_keyboard, 
    get_student_skip_keyboard, 
    get_student_profile_confirmation_keyboard,
    get_student_goal_keyboard,
    get_student_edit_profile_keyboard, 
    get_start_test_keyboard, 
    get_about_test_keyboard,
    get_improve_grades_keyboard, 
    get_explore_courses_keyboard, 
    get_city_keyboard,
    get_calendar_with_manual_input_keyboard,
    get_course_categories_keyboard,
    get_student_welcome_keyboard 
)
from app.keyboards.reply import get_student_main_menu_keyboard, get_share_phone_keyboard
from app.utils.helpers import calculate_age
from app.handlers.stem_navigator import show_test_results

router = Router()

async def clear_history(chat_id: int, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    message_ids = user_data.get('message_ids_to_delete', [])
    for msg_id in reversed(message_ids):
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass 
    await state.update_data(message_ids_to_delete=[])

async def append_message_ids(state: FSMContext, *messages: types.Message | types.CallbackQuery):
    user_data = await state.get_data()
    ids = user_data.get('message_ids_to_delete', [])
    for msg_or_cb in messages:
        if msg_or_cb:
            message = msg_or_cb if isinstance(msg_or_cb, types.Message) else msg_or_cb.message
            if message and message.message_id not in ids:
                ids.append(message.message_id)
    await state.update_data(message_ids_to_delete=ids)

async def edit_and_save_message(
    state: FSMContext,
    message: types.Message,
    text: str,
    bot: Bot,
    reply_markup=None,
    parse_mode=None,
    disable_web_page_preview=None
):
    try:
        edited = await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
        await append_message_ids(state, edited)
        return edited
    except Exception:
        new_msg = await bot.send_message(chat_id=message.chat.id, text=text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
        await append_message_ids(state, new_msg)
        return new_msg

@router.callback_query(StudentRegistration.confirming_creation, F.data == "student_create_profile")
async def ask_if_registered_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(StudentRegistration.asking_if_registered)
    await state.update_data(message_ids_to_delete=[callback.message.message_id]) 
    await callback.message.edit_text(
        text=lexicon[lang]['student-ask-if-registered'],
        reply_markup=get_yes_no_keyboard(lexicon, lang)
    )
    await callback.answer()

@router.callback_query(StudentRegistration.asking_if_registered)
async def handle_is_registered_answer(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    if callback.data == 'yes':
        await state.set_state(StudentRegistration.entering_existing_phone)
        await callback.message.edit_text(text=lexicon[lang]['student-enter-phone-for-search'])
    else:
        await state.set_state(StudentRegistration.entering_first_name)
        await callback.message.edit_text(lexicon[lang]['prompt-enter-first-name'])
    await callback.answer()

@router.message(StudentRegistration.entering_existing_phone)
async def process_existing_phone(message: Message, state: FSMContext, lexicon: dict):
    phone = message.text.strip()
    lang = (await state.get_data()).get('language', 'ru')
    searching_msg = await message.answer(lexicon[lang]['searching-user'])
    await append_message_ids(state, message, searching_msg)
    exode_data = find_user_by_phone(phone)
    user_info, profile, full_name = None, None, ""
    if exode_data and exode_data.get('user'):
        user_info = exode_data['user']
        profile = user_info.get('profile') 
    if profile and profile.get('firstName'):
        full_name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
    
    if user_info:
        if not full_name:
            confirmation_text = lexicon[lang]['student-found-no-name'].format(phone=phone)
        else:
            confirmation_text = lexicon[lang]['student-found-confirm'].format(name=full_name)
        
        await state.update_data(found_user_data=user_info)
        await state.set_state(StudentRegistration.confirming_found_user)
        conf_msg = await message.answer(text=confirmation_text, reply_markup=get_yes_no_keyboard(lexicon, lang, "confirm_found_user_yes", "confirm_found_user_no"))
        await append_message_ids(state, conf_msg)
    else:
        await start_new_registration_flow(message, state, lexicon, user_found_but_empty=False)

@router.callback_query(StudentRegistration.confirming_found_user)
async def handle_found_user_confirmation(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language', 'ru')

    if callback.data == 'confirm_found_user_yes':
        user_data = await state.get_data()
        found_user = user_data.get('found_user_data', {})
        profile = found_user.get('profile', {})

        bdate = profile.get('bdate')
        dob_str = datetime.strptime(bdate, '%Y-%m-%d').strftime('%d.%m.%Y') if bdate else None
        
        await state.update_data(
            student_first_name=profile.get('firstName'),
            student_last_name=profile.get('lastName'),
            student_phone=found_user.get('phone'),
            student_dob=dob_str,
            found_exode_user=True
        )
        
        next_msg = None
        if not profile.get('firstName'):
            await state.set_state(StudentRegistration.entering_first_name)
            next_msg = await callback.message.answer(f"Отлично! Давайте дополним ваш профиль.\n\n" + lexicon[lang]['prompt-enter-first-name'])
        elif not dob_str:
            await state.set_state(StudentRegistration.entering_dob)
            next_msg = await callback.message.answer(f"Отлично, {profile.get('firstName')}! Теперь укажите вашу дату рождения:", reply_markup=await get_calendar_with_manual_input_keyboard(lexicon, lang))
        else:
            await state.set_state(StudentRegistration.entering_city)
            next_msg = await callback.message.answer(f"Отлично, {profile.get('firstName')}! Теперь выберите ваш город:", reply_markup=get_city_keyboard(lang))
        
        await state.update_data(message_ids_to_delete=[next_msg.message_id])

    else:
        await start_new_registration_flow(callback.message, state, lexicon, user_found_but_empty=True)
    
    await callback.answer()

async def start_new_registration_flow(message: types.Message, state: FSMContext, lexicon: dict, user_found_but_empty: bool):
    await clear_history(message.chat.id, state, message.bot)
    lang = (await state.get_data()).get('language', 'ru')
    prompt_key = 'student-not-found-start-reg' if not user_found_but_empty else 'student-is-not-you-start-reg'
    await state.set_state(StudentRegistration.entering_first_name)
    next_msg = await message.answer(lexicon[lang].get(prompt_key) + "\n\n" + lexicon[lang]['prompt-enter-first-name'])
    await state.update_data(message_ids_to_delete=[next_msg.message_id])

@router.message(StudentRegistration.entering_first_name)
async def student_first_name_handler(message: Message, state: FSMContext, lexicon: dict):
    await state.update_data(student_first_name=message.text.strip())
    user_data = await state.get_data()
    lang = user_data.get('language')
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_student_confirmation_screen(message, state, lexicon)
    else: 
        await state.set_state(StudentRegistration.entering_last_name)
        next_msg = await message.answer(lexicon[lang]['prompt-enter-last-name'])
        await append_message_ids(state, message, next_msg)

@router.message(StudentRegistration.entering_last_name)
async def student_last_name_handler(message: Message, state: FSMContext, lexicon: dict):
    await state.update_data(student_last_name=message.text.strip())
    user_data = await state.get_data()
    lang = user_data.get('language')
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_student_confirmation_screen(message, state, lexicon)
    else:
        await state.set_state(StudentRegistration.entering_dob)
        next_msg = await message.answer("Выберите дату своего рождения:", reply_markup=await get_calendar_with_manual_input_keyboard(lexicon, lang))
        await append_message_ids(state, message, next_msg)

@router.callback_query(StudentRegistration.entering_dob, SimpleCalendarCallback.filter())
async def process_calendar_selection(callback: types.CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await state.update_data(student_dob=date.strftime("%d.%m.%Y"))
        user_data = await state.get_data()
        if user_data.get("editing_during_registration"):
            await state.update_data(editing_during_registration=False)
            await show_student_confirmation_screen(callback.message, state, lexicon)
        else:
            await state.set_state(StudentRegistration.entering_city)
            await callback.message.edit_text(lexicon[lang]['student-enter-city-prompt'], reply_markup=get_city_keyboard(lang))
    await callback.answer()

@router.callback_query(StudentRegistration.entering_dob, F.data == "manual_dob_input")
async def manual_dob_input_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.entering_dob_manually)
    await callback.message.edit_text(lexicon[lang]['student-enter-age-prompt'])
    await callback.answer()

@router.message(StudentRegistration.entering_dob_manually, F.text)
async def process_manual_dob_input(message: Message, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    try:
        datetime.strptime(message.text, '%d.%m.%Y')
        await state.update_data(student_dob=message.text)
        user_data = await state.get_data()
        if user_data.get("editing_during_registration"):
            await state.update_data(editing_during_registration=False)
            await show_student_confirmation_screen(message, state, lexicon)
        else:
            next_msg = await message.answer(lexicon[lang]['student-enter-city-prompt'], reply_markup=get_city_keyboard(lang))
            await append_message_ids(state, message, next_msg)
            await state.set_state(StudentRegistration.entering_city)
    except ValueError:
        error_msg = await message.answer(lexicon[lang]['student-dob-error'])
        await append_message_ids(state, message, error_msg)

@router.callback_query(StudentRegistration.entering_city, F.data.startswith("city_") | (F.data == "manual_city_input"))
async def student_city_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    if callback.data == "manual_city_input":
        await state.set_state(StudentRegistration.entering_city_manually)
        await callback.message.edit_text("Пожалуйста, напишите название вашего города:")
        await callback.answer()
        return
    city = callback.data.split("_", 1)[1]
    await state.update_data(student_city=city)
    user_data = await state.get_data()
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_student_confirmation_screen(callback.message, state, lexicon)
    else:
        await callback.message.delete()
        next_msg = await callback.message.answer(lexicon[lang]['student-enter-phone-prompt'], reply_markup=get_share_phone_keyboard(lexicon, lang))
        await append_message_ids(state, next_msg)
        await state.set_state(StudentRegistration.entering_phone)
    await callback.answer()

@router.message(StudentRegistration.entering_city_manually)
async def process_manual_student_city_input(message: Message, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.update_data(student_city=message.text.strip())
    user_data = await state.get_data()
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_student_confirmation_screen(message, state, lexicon)
    else:
        next_msg = await message.answer(lexicon[lang]['student-enter-phone-prompt'], reply_markup=get_share_phone_keyboard(lexicon, lang))
        await append_message_ids(state, message, next_msg)
        await state.set_state(StudentRegistration.entering_phone)

@router.message(StudentRegistration.entering_phone, F.text | F.contact)
async def student_phone_handler(message: Message, state: FSMContext, lexicon: dict):
    phone_number = message.contact.phone_number if message.contact else message.text.strip()
    await state.update_data(student_phone=phone_number)
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    await message.answer("Спасибо!", reply_markup=ReplyKeyboardRemove())
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_student_confirmation_screen(message, state, lexicon)
    else:
        await state.set_state(StudentRegistration.entering_parent_name)
        dob = user_data.get('student_dob')
        age = calculate_age(dob)
        keyboard = get_student_skip_keyboard(lexicon, lang) if age and age >= 18 else None
        next_msg = await message.answer(lexicon[lang]['student-enter-parent-name-prompt'], reply_markup=keyboard)
        await append_message_ids(state, message, next_msg)

@router.message(StudentRegistration.entering_parent_name)
async def parent_name_handler(message: types.Message, state: FSMContext, lexicon: dict):
    await state.update_data(parent_name=message.text.strip())
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    if user_data.get("editing_during_registration"):
        await state.update_data(editing_during_registration=False)
        await show_student_confirmation_screen(message, state, lexicon)
    else:
        next_msg = await message.answer(lexicon[lang]['student-enter-parent-phone-prompt'])
        await append_message_ids(state, message, next_msg)
        await state.set_state(StudentRegistration.entering_parent_phone)

@router.message(StudentRegistration.entering_parent_phone)
async def parent_phone_handler(message: types.Message, state: FSMContext, lexicon: dict):
    await state.update_data(parent_phone=message.text.strip())
    await append_message_ids(state, message)
    await show_student_confirmation_screen(message, state, lexicon)
    
@router.callback_query(StudentRegistration.entering_parent_name, F.data == "skip_parent_contact")
async def skip_parent_contact_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await state.update_data(parent_name=None, parent_phone=None)
    await show_student_confirmation_screen(callback.message, state, lexicon)
    await callback.answer()

async def show_student_confirmation_screen(message: types.Message, state: FSMContext, lexicon: dict):
    await clear_history(message.chat.id, state, message.bot)
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    parent_name = user_data.get('parent_name')
    parent_phone = user_data.get('parent_phone')
    
    if parent_name and parent_phone:
        parent_contact = f"{parent_name}, {parent_phone}"
    elif parent_name:
        parent_contact = parent_name
    elif parent_phone:
        parent_contact = parent_phone
    else:
        parent_contact = lexicon[lang].get('not-specified', 'Не указан')
    
    dob = user_data.get('student_dob')
    age = calculate_age(dob)
    phone = user_data.get('student_phone') or lexicon[lang].get('not-specified', 'Не указан')
    
    text = lexicon[lang]['student-profile-confirmation'].format(
        first_name=user_data.get('student_first_name', ''),
        last_name=user_data.get('student_last_name', ''),
        dob=dob or 'N/A',
        age=age or 'N/A',
        phone=phone,
        city=user_data.get('student_city', ''),
        parent_contact=parent_contact
    )
    
    conf_msg = await message.answer(text, reply_markup=get_student_profile_confirmation_keyboard(lexicon, lang))
    await append_message_ids(state, conf_msg)
    await state.set_state(StudentRegistration.confirming_profile)
    
    if isinstance(message, types.Message) and message.message_id != conf_msg.message_id:
        try:
            await message.delete()
        except:
            pass

@router.callback_query(StudentRegistration.confirming_profile, F.data == "student_confirm_profile")
async def confirm_student_profile_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    await clear_history(callback.message.chat.id, state, callback.bot)
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    data_to_save = {
        'Telegram ID': callback.from_user.id,
        'Имя': user_data.get('student_first_name'),
        'Фамилия': user_data.get('student_last_name'),
        'Дата рождения': user_data.get('student_dob'),
        'Город': user_data.get('student_city'),
        'Телефон': user_data.get('student_phone'),
        'Имя родителя': user_data.get('parent_name'),
        'Телефон родителя': user_data.get('parent_phone'),
        'Язык': user_data.get('language'),
        'Роль': 'student'
    }
    
    registration_manager.add_student(data_to_save)
    
    consent_text = lexicon[lang]['student-exode-consent-prompt']
    
    if user_data.get('found_exode_user'):
        payload = {
            'phone': user_data.get('student_phone'),
            'tgId': callback.from_user.id
        }
        
        result = upsert_user(payload)
        
        await state.set_state(StudentRegistration.choosing_goal)
        next_msg = await callback.message.answer(
            lexicon[lang]['student-choose-goal-prompt'], 
            reply_markup=get_student_goal_keyboard(lexicon, lang)
        )
        await state.update_data(message_ids_to_delete=[next_msg.message_id])
    else:
        await state.set_state(StudentRegistration.confirming_exode_creation)
        consent_msg = await callback.message.answer(
            consent_text, 
            reply_markup=get_consent_keyboard(lexicon, lang),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        await state.update_data(message_ids_to_delete=[consent_msg.message_id])
        
    await callback.answer()

@router.callback_query(StudentRegistration.confirming_exode_creation)
async def handle_exode_creation_consent(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    if callback.data == "consent_yes":
        dob_str = user_data.get('student_dob')
        try:
            dob_exode = datetime.strptime(dob_str, '%d.%m.%Y').strftime('%Y-%m-%d')
        except:
            dob_exode = None
        
        payload = {
            'phone': user_data.get('student_phone'),
            'tgId': callback.from_user.id,
            'profile': {
                'firstName': user_data.get('student_first_name'),
                'lastName': user_data.get('student_last_name'),
                'bdate': dob_exode,
                'role': 'Student'
            }
        }
        
        result = upsert_user(payload)
        
        if result:
            success_msg = await callback.message.answer(
                lexicon[lang].get('exode-account-created', 'Ваш аккаунт успешно создан в системе Exode!')
            )
            await append_message_ids(state, success_msg)
        else:
            error_msg = await callback.message.answer(
                lexicon[lang].get('exode-creation-error', 'Не удалось создать аккаунт. Вы сможете использовать бота без этого.')
            )
            await append_message_ids(state, error_msg)
    
    await state.set_state(StudentRegistration.choosing_goal)
    goal_msg = await callback.message.answer(
        lexicon[lang]['student-choose-goal-prompt'],
        reply_markup=get_student_goal_keyboard(lexicon, lang)
    )
    await state.update_data(message_ids_to_delete=[goal_msg.message_id])
    await callback.answer()


@router.callback_query(StudentRegistration.confirming_creation, F.data == "postpone_registration")
async def postpone_student_creation_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    # (Не очищаем историю, просто удаляем сообщение)
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')

    await state.set_state(None) 

    
    menu_message = await callback.message.answer(
        text=lexicon[lang]['main-menu-welcome'], 
        reply_markup=get_student_main_menu_keyboard(lexicon, lang)
    )

    await state.update_data(main_menu_message_id=menu_message.message_id)
    await callback.answer()

@router.callback_query(StudentRegistration.entering_last_name, F.data == "back_to_first_name")
async def back_to_first_name_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.entering_first_name)
    next_msg = await callback.message.answer(lexicon[lang]['prompt-enter-first-name'])
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.entering_dob, F.data == "back_to_last_name")
async def back_to_last_name_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.entering_last_name)
    next_msg = await callback.message.answer(lexicon[lang]['prompt-enter-last-name'])
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.entering_city, F.data == "back_to_dob")
async def back_to_dob_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.entering_dob)
    next_msg = await callback.message.answer("Выберите дату своего рождения:", reply_markup=await get_calendar_with_manual_input_keyboard(lexicon, lang))
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.entering_phone, F.data == "back_to_city")
async def back_to_city_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.entering_city)
    next_msg = await callback.message.answer(lexicon[lang]['student-enter-city-prompt'], reply_markup=get_city_keyboard(lang))
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.entering_parent_name, F.data == "back_to_phone_input")
async def back_to_student_phone_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.entering_phone)
    next_msg = await callback.message.answer(lexicon[lang]['student-enter-phone-prompt'], reply_markup=get_share_phone_keyboard(lexicon, lang))
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.entering_parent_phone, F.data == "back_to_parent_name")
async def back_to_parent_name_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    user_data = await state.get_data()
    dob = user_data.get('student_dob')
    age = calculate_age(dob)
    keyboard = get_student_skip_keyboard(lexicon, lang) if age and age >= 18 else None
    await state.set_state(StudentRegistration.entering_parent_name)
    next_msg = await callback.message.answer(lexicon[lang]['student-enter-parent-name-prompt'], reply_markup=keyboard)
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.confirming_profile, F.data == "back_to_parent_contact")
async def back_to_parent_phone_from_confirm_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await clear_history(callback.message.chat.id, state, callback.bot)
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.entering_parent_phone)
    next_msg = await callback.message.answer(lexicon[lang]['student-enter-parent-phone-prompt'])
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.confirming_profile, F.data == "student_edit_profile")
async def student_edit_profile_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.editing_profile)
    await callback.message.edit_text(lexicon[lang]['student-choose-field-to-edit'], reply_markup=get_student_edit_profile_keyboard(lexicon, lang))
    await callback.answer()

@router.callback_query(StudentRegistration.editing_profile, F.data == "back_to_student_confirmation")
async def back_to_student_confirmation_from_edit_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await show_student_confirmation_screen(callback.message, state, lexicon)
    await callback.answer()

@router.callback_query(StudentRegistration.editing_profile, F.data.startswith("edit_student_"))
async def edit_student_field_registration_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    field_data = callback.data.replace("edit_student_", "")
    await state.update_data(editing_during_registration=True)
    prompts = { 
        "first_name": lexicon[lang]['prompt-enter-first-name'], 
        "last_name": lexicon[lang]['prompt-enter-last-name'], 
        "age": "Выберите новую дату рождения:", 
        "city": lexicon[lang]['student-enter-city-prompt'], 
        "phone": lexicon[lang]['student-enter-phone-prompt'], 
        "parent_contact": lexicon[lang]['student-enter-parent-name-prompt'] 
    }
    keyboards = { 
        "age": await get_calendar_with_manual_input_keyboard(lexicon, lang), 
        "city": get_city_keyboard(lang), 
        "phone": get_share_phone_keyboard(lexicon, lang) 
    }
    states = { 
        "first_name": StudentRegistration.entering_first_name, 
        "last_name": StudentRegistration.entering_last_name, 
        "age": StudentRegistration.entering_dob, 
        "city": StudentRegistration.entering_city, 
        "phone": StudentRegistration.entering_phone, 
        "parent_contact": StudentRegistration.entering_parent_name 
    }
    target_state, prompt_text = states.get(field_data), prompts.get(field_data)
    if not target_state: 
        return await callback.answer("Ошибка: Неизвестное поле.", show_alert=True)
    await state.set_state(target_state)
    await callback.message.delete()
    next_msg = await callback.message.answer(prompt_text, reply_markup=keyboards.get(field_data))
    await state.update_data(message_ids_to_delete=[next_msg.message_id])
    await callback.answer()

@router.callback_query(StudentRegistration.choosing_goal, F.data.startswith("goal_"))
async def student_goal_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    goal = callback.data.split("_")[1]

    if goal in ("university", "profession"):
        text = lexicon[lang]['student-goal-university-text'] if goal == "university" else lexicon[lang]['student-goal-profession-text']
        from_profession = (goal == "profession")
        
        await edit_and_save_message(
            state,
            callback.message,
            text,
            callback.bot,
            get_start_test_keyboard(lexicon, lang, from_profession_branch=from_profession)
        )
    elif goal == "grades":
        await edit_and_save_message(
            state,
            callback.message,
            lexicon[lang]['student-goal-grades-text'],
            callback.bot,
            get_improve_grades_keyboard(lexicon, lang)
        )
    elif goal == "explore":
        await edit_and_save_message(
            state,
            callback.message,
            lexicon[lang]['student-goal-explore-text'],
            callback.bot,
            get_explore_courses_keyboard(lexicon, lang)
        )
    
    await callback.answer()

@router.callback_query(F.data == "start_test_now")
async def start_test_now_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.set_state(StemNavigator.showing_test_info)
    
    await edit_and_save_message(
        state,
        callback.message,
        lexicon[lang]['about-test-text'],
        callback.bot,
        get_about_test_keyboard(lexicon, lang),
        parse_mode='HTML'
    )
    
    await callback.answer()

@router.callback_query(F.data == "postpone_action")
async def postpone_action_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    
    await state.clear()

    try:
        await callback.message.delete()
    except:
        pass

    menu_message = await callback.message.answer(
        text=lexicon[lang]['main-menu-welcome'],
        reply_markup=get_student_main_menu_keyboard(lexicon, lang)
    )
    await state.update_data(main_menu_message_id=menu_message.message_id) 
    await callback.answer()

@router.callback_query(F.data.in_({"see_ai_assistant", "show_intro_courses"}))
async def coming_soon_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await callback.answer(text=lexicon[lang]['coming-soon'], show_alert=True)

@router.callback_query(F.data == "find_subject_courses")
async def find_subject_courses_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, courses_manager: CoursesGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    all_courses = courses_manager.get_courses()
    if not all_courses:
        await callback.answer("К сожалению, список курсов сейчас недоступен.", show_alert=True)
        return

    categories = sorted(list(set(c['Категория'] for c in all_courses if c.get('Категория'))))
    
    await state.set_state(Programs.choosing_direction)
    await edit_and_save_message(
        state, callback.message,
        "Выберите направление, которое вас интересует:",
        callback.bot,
        get_course_categories_keyboard(categories, lexicon, lang)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_goal_select")
async def back_to_goal_select_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language')
    await state.set_state(StudentRegistration.choosing_goal)
    
    await edit_and_save_message(
        state,
        callback.message,
        lexicon[lang]['student-choose-goal-prompt'],
        callback.bot,
        get_student_goal_keyboard(lexicon, lang)
    )
    
    await callback.answer()

@router.message(F.text.in_({"🧭 STEM-навигатор", "🧭 STEM-navigator"}))
async def student_stem_navigator_start(message: types.Message, state: FSMContext, lexicon: dict):
    await message.delete()
    user_data = await state.get_data()
    if menu_msg_id := user_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')

    if user_data.get("test_results"):
        mock_callback_message = await message.answer("Загружаю ваши предыдущие результаты...")
        mock_callback = types.CallbackQuery(
            id="mock_callback_id_student", from_user=message.from_user, chat_instance="",
            message=mock_callback_message, data="show_results"
        )
        
        await show_test_results(mock_callback, state, lexicon)
        
    else:
        await state.set_state(StemNavigator.showing_test_info)
        await message.answer(
            text=lexicon[lang]['about-test-text'],
            reply_markup=get_about_test_keyboard(lexicon, lang)
        )

@router.message(F.text.in_({"🤖 AI-ассистент Stemi", "🤖 YI-assistent"}))
async def ai_assistant_stub_handler(message: types.Message, state: FSMContext, lexicon: dict):
    await message.delete()
    user_data = await state.get_data()
    if menu_msg_id := user_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass
    lang = (await state.get_data()).get('language', 'ru')
    await message.answer(lexicon[lang]['coming-soon'])