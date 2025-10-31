from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

# Импортируем все необходимые состояния, менеджеры и клавиатуры
from app.states.registration import Programs
from app.utils.google_sheets import CoursesGSheet
from app.keyboards.inline import (
    get_course_categories_keyboard,
    get_course_subcategories_keyboard,
    get_specific_courses_keyboard,
    get_course_card_keyboard
)

router = Router()

# --- ШАГ 1: ВЫБОР КАТЕГОРИИ (Программирование, Математика) ---

@router.message(F.text.in_({"📚 Программы обучения", "📚 O'quv dasturlari"}))
async def programs_start_handler(message: types.Message, state: FSMContext, lexicon: dict, courses_manager: CoursesGSheet):
    await message.delete()
    
    user_data = await state.get_data()
    if menu_msg_id := user_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass 
    lang = (await state.get_data()).get('language', 'ru')
    
    all_courses = courses_manager.get_courses()
    if not all_courses:
        await message.answer("К сожалению, список курсов сейчас недоступен.")
        return

    categories = sorted(list(set(c['Категория'] for c in all_courses if c.get('Категория'))))
    
    await state.set_state(Programs.choosing_direction)
    await message.answer(
        "Выберите направление, которое вас интересует:",
        reply_markup=get_course_categories_keyboard(categories, lexicon, lang)
    )

# --- ШАГ 2: УМНЫЙ ВЫБОР ПОДКАТЕГОРИИ ---

@router.callback_query(Programs.choosing_direction, F.data.startswith("category_"))
async def category_selected_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, courses_manager: CoursesGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    selected_category = callback.data.split('_', 1)[1]
    
    await state.update_data(selected_category=selected_category)
    all_courses = courses_manager.get_courses()
    
    subcategories = sorted(list(set(
        c['Подкатегория'] for c in all_courses 
        if c.get('Категория') == selected_category and c.get('Подкатегория')
    )))

    if len(subcategories) == 1:
        selected_subcategory = subcategories[0]
        await state.update_data(selected_subcategory=selected_subcategory)

        specific_courses = [
            c for c in all_courses 
            if c.get('Категория') == selected_category 
            and c.get('Подкатегория') == selected_subcategory
            and c.get('language') == lang
        ]
        
        await state.update_data(specific_courses_list=specific_courses)
        await state.set_state(Programs.choosing_course)
        
        await callback.message.edit_text(
            f"Вы выбрали: {selected_category}\nДоступные курсы:",
            reply_markup=get_specific_courses_keyboard(specific_courses, lexicon, lang)
        )

    else:
        await state.set_state(Programs.choosing_subcategory)
        await callback.message.edit_text(
            f"Вы выбрали: {selected_category}\nТеперь выберите тему:",
            reply_markup=get_course_subcategories_keyboard(subcategories, lexicon, lang)
        )
    
    await callback.answer()

# --- ШАГ 3: ВЫБОР КОНКРЕТНОГО КУРСА ---
@router.callback_query(Programs.choosing_subcategory, F.data.startswith("subcategory_"))
async def subcategory_selected_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, courses_manager: CoursesGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    selected_subcategory = callback.data.split('_', 1)[1]
    
    user_data = await state.get_data()
    selected_category = user_data.get('selected_category')

    await state.update_data(selected_subcategory=selected_subcategory)
    all_courses = courses_manager.get_courses()

    specific_courses = [
        c for c in all_courses 
        if c.get('Категория') == selected_category 
        and c.get('Подкатегория') == selected_subcategory
        and c.get('language') == lang
    ]
    
    await state.update_data(specific_courses_list=specific_courses)
    await state.set_state(Programs.choosing_course)
    await callback.message.edit_text(
        f"Вы выбрали: {selected_subcategory}\nДоступные курсы:",
        reply_markup=get_specific_courses_keyboard(specific_courses, lexicon, lang)
    )
    await callback.answer()

# --- ШАГ 4: ПОКАЗ КАРТОЧКИ КУРСА ---
@router.callback_query(Programs.choosing_course, F.data.startswith("course_"))
async def course_selected_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    course_index = int(callback.data.split('_', 1)[1])
    user_data = await state.get_data()
    specific_courses = user_data.get('specific_courses_list', [])
    target_course = specific_courses[course_index]

    await state.set_state(Programs.viewing_course)
    
    card_text = (
        f"<b>{target_course.get('Название курса', 'Название не указано')}</b>\n\n"
        f"{target_course.get('Описание', 'Описание скоро будет добавлено.')}\n\n"
        f"<b>Длительность:</b> {target_course.get('Длительность')}\n"
        f"<b>Цена:</b> {target_course.get('Цена')}"
    )
    
    course_id = target_course.get('course_id', 'unknown') 

    await callback.message.edit_text(
        card_text,
        reply_markup=get_course_card_keyboard(lexicon, lang, course_id)
    )
    await callback.answer()

# --- ОБРАБОТЧИКИ КНОПОК "НАЗАД" ---
@router.callback_query(F.data == "back_to_categories")
async def back_to_categories_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, courses_manager: CoursesGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    all_courses = courses_manager.get_courses()
    categories = sorted(list(set(c['Категория'] for c in all_courses if c.get('Категория'))))
    await state.set_state(Programs.choosing_direction)
    await callback.message.edit_text(
        "Выберите направление, которое вас интересует:",
        reply_markup=get_course_categories_keyboard(categories, lexicon, lang)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_subcategories")
async def back_to_subcategories_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, courses_manager: CoursesGSheet):
    lang = (await state.get_data()).get('language', 'ru')
    user_data = await state.get_data()
    selected_category = user_data.get('selected_category')

    all_courses = courses_manager.get_courses()
    subcategories = sorted(list(set(
        c['Подкатегория'] for c in all_courses 
        if c.get('Категория') == selected_category and c.get('Подкатегория')
    )))

    if len(subcategories) <= 1:
        await back_to_categories_handler(callback, state, lexicon, courses_manager)
    else:
        await state.set_state(Programs.choosing_subcategory)
        await callback.message.edit_text(
            f"Вы выбрали: {selected_category}\nТеперь выберите тему:",
            reply_markup=get_course_subcategories_keyboard(subcategories, lexicon, lang)
        )
        await callback.answer()

# ЗАГЛУШКА ДЛЯ КНОПКИ "ЗАПИСАТЬСЯ"
@router.callback_query(Programs.viewing_course, F.data.startswith("enroll_"))
async def enroll_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await callback.answer("Спасибо за ваш интерес! Скоро мы добавим функцию онлайн-записи.", show_alert=True)

