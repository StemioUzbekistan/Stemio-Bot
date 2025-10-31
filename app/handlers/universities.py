from aiogram import Router, F, types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.states.registration import Universities 
from app.utils.google_sheets import UniversitiesGSheet
from app.utils.locations import CITIES_RU 
from app.core.config import PRIVATE_UNIVERSITIES_SHEET_ID, FOREIGN_UNIVERSITIES_SHEET_ID

router = Router()
ITEMS_PER_PAGE = 5 

# Поля для карточки программы
VISIBLE_PROGRAM_FIELDS = [ 
    "Название факультета", "Название программы", "Язык обучения", "Форма обучения", 
    "Экзамены", "Стоимость", "Прием документов", "Минимальные баллы для поступления", 
    "Продолжительность", "Заочное обучение", "Вечернее обучение", "Онлайн обучение", 
    "Стипендия", "Наличие общежития", "Количество мест", "Квота на бюджет", "Квота на платное обучение" 
]

# --- КЛАВИАТУРЫ ---

def get_cities_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    for city_name in CITIES_RU:
        builder.row(types.InlineKeyboardButton(text=city_name, callback_data=f"uni_city_{city_name}"))
    builder.row(types.InlineKeyboardButton(text=lexicon.get(lang, {}).get('button-back', 'Back'), callback_data="back_to_main_menu"))
    return builder.as_markup()

def get_uni_types_keyboard(lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🎓 Государственные", callback_data="uni_type_Государственный"))
    builder.row(types.InlineKeyboardButton(text="🏢 Частные", callback_data="uni_type_Частный"))
    builder.row(types.InlineKeyboardButton(text="🌍 Иностранные", callback_data="uni_type_Иностранный"))
    builder.row(types.InlineKeyboardButton(text=lexicon.get(lang, {}).get('button-back', 'Back'), callback_data="back_to_cities"))
    return builder.as_markup()

def get_paginated_keyboard(items: list, page: int, data_prefix: str, back_callback: str, lexicon: dict, lang: str):
    builder = InlineKeyboardBuilder()
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    
    current_page_items = items[start_index:end_index]
    
    for item_name in current_page_items:
        try:
            actual_index = items.index(item_name, start_index, end_index + len(items))
        except ValueError:
            actual_index = start_index + current_page_items.index(item_name) 

        builder.row(types.InlineKeyboardButton(text=str(item_name), callback_data=f"{data_prefix}_{actual_index}"))
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"page_{data_prefix}_{page - 1}"))
    if end_index < len(items):
        nav_buttons.append(types.InlineKeyboardButton(text="➡️", callback_data=f"page_{data_prefix}_{page + 1}"))
    
    if nav_buttons: builder.row(*nav_buttons)
    builder.row(types.InlineKeyboardButton(text=lexicon.get(lang, {}).get('button-back', 'Back'), callback_data=back_callback))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@router.message(F.text.in_({"🎓 Вузы", "🎓 OTMlar"}))
async def universities_start_handler(message: types.Message, state: FSMContext, lexicon: dict):
    await message.delete()
    user_data = await state.get_data()
    if menu_msg_id := user_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass
    
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(Universities.choosing_city)
    await message.answer("Выберите город:", reply_markup=get_cities_keyboard(lexicon, lang))

@router.callback_query(Universities.choosing_city, F.data.startswith("uni_city_"))
async def city_selected_handler(
    callback: types.CallbackQuery, 
    state: FSMContext, 
    lexicon: dict, 
    state_uni_ids_by_city: dict
):
    selected_city = callback.data.split('_', 2)[2]
    lang = (await state.get_data()).get('language', 'ru')
    
    state_uni_ids = state_uni_ids_by_city

    if not state_uni_ids.get(selected_city) and not PRIVATE_UNIVERSITIES_SHEET_ID and not FOREIGN_UNIVERSITIES_SHEET_ID:
         await callback.answer(f"В г. {selected_city} вузы пока не добавлены.", show_alert=True)
         return
            
    await state.update_data(selected_city=selected_city)
    await state.set_state(Universities.choosing_uni_type)
    await callback.message.edit_text(
        f"Вы выбрали город: {selected_city}.\nТеперь выберите тип вуза:",
        reply_markup=get_uni_types_keyboard(lexicon, lang)
    )
    await callback.answer()

@router.callback_query(Universities.choosing_uni_type, F.data.startswith("uni_type_"))
async def uni_type_selected_handler(
    callback: types.CallbackQuery, 
    state: FSMContext, 
    lexicon: dict, 
    universities_manager: UniversitiesGSheet, 
    state_uni_ids_by_city: dict
):
    selected_type = callback.data.split('_', 2)[2] 
    user_data = await state.get_data()
    selected_city = user_data.get("selected_city")
    lang = user_data.get('language', 'ru')
    
    selected_sheet_id = None
    
    if selected_type == "Государственный":
        state_uni_ids = state_uni_ids_by_city
        selected_sheet_id = state_uni_ids.get(selected_city)
        if not selected_sheet_id:
            await callback.answer(f"Не найден ID таблицы для гос. вузов в г. {selected_city}.", show_alert=True)
            return
    
    elif selected_type == "Частный":
        selected_sheet_id = PRIVATE_UNIVERSITIES_SHEET_ID
    
    elif selected_type == "Иностранный":
        selected_sheet_id = FOREIGN_UNIVERSITIES_SHEET_ID
        
    if not selected_sheet_id:
        await callback.answer(f"Ошибка: ID таблицы для '{selected_type}' не найден в .env", show_alert=True)
        return

    city_filter = selected_city if selected_type in ["Частный", "Иностранный"] else None
    
    all_universities_in_file = universities_manager.get_universities_by_city_and_type(
        sheet_id=selected_sheet_id,
        city=city_filter 
    )

    if not all_universities_in_file:
        await callback.answer(f"В г. {selected_city} не найдены вузы типа '{selected_type}'.", show_alert=True)
        return
        
    await state.set_state(Universities.choosing_university)
    await state.update_data(
        page=0, 
        uni_type=selected_type, 
        current_sheet_id=selected_sheet_id, 
        filtered_universities=all_universities_in_file
    )
    
    uni_names = [uni.get("Наименования ВОУ", "N/A") for uni in all_universities_in_file]
    
    await callback.message.edit_text(
        f"<b>{selected_city} / {selected_type}</b>\n\nВыберите вуз:",
        reply_markup=get_paginated_keyboard(
            items=uni_names, page=0, data_prefix="uni", back_callback="back_to_uni_type", lexicon=lexicon, lang=lang
        )
    )
    await callback.answer()

@router.callback_query(Universities.choosing_university, F.data.startswith("uni_"))
async def university_selected_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, universities_manager: UniversitiesGSheet):
    university_index = int(callback.data.split('_')[1])
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    selected_university = user_data.get("filtered_universities", [])[university_index]
    
    sheet_name = selected_university.get('sheet_name')
    if not sheet_name:
        await callback.answer(f"Ошибка: Для ВУЗа '{selected_university.get('Наименования ВОУ')}' не указан 'sheet_name' в таблице.", show_alert=True)
        return

    all_programs = universities_manager.get_faculties_by_sheet_name(sheet_name)
    
    if not all_programs:
        await callback.answer(f"Для этого вуза факультеты (на листе '{sheet_name}') еще не добавлены.", show_alert=True)
        return
        
    unique_faculties = sorted(list(set(
        p.get("Название факультета") for p in all_programs if p.get("Название факультета")
    )))
    
    if not unique_faculties:
         await callback.answer(f"В таблице '{sheet_name}' не найдена колонка 'Название факультета' или она пуста.", show_alert=True)
         return
    
    await state.update_data(
        all_programs=all_programs, 
        unique_faculties=unique_faculties, 
        selected_university_index=university_index
    )
    await state.set_state(Universities.choosing_faculty)
    
    await callback.message.edit_text(
        f"<b>{selected_university.get('Наименования ВОУ')}</b>\n\nВыберите факультет:",
        reply_markup=get_paginated_keyboard(
            items=unique_faculties, page=0, data_prefix="faculty", back_callback="back_to_universities", lexicon=lexicon, lang=lang
        )
    )
    await callback.answer()


@router.callback_query(Universities.choosing_faculty, F.data.startswith("faculty_"))
async def faculty_selected_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    faculty_index = int(callback.data.split('_')[1])
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    selected_faculty_name = user_data.get("unique_faculties", [])[faculty_index]
    all_programs = user_data.get("all_programs", [])
    
    programs_in_faculty = [
        p for p in all_programs 
        if p.get("Название факультета") == selected_faculty_name
    ]
    
    program_names = [p.get("Название программы", "N/A") for p in programs_in_faculty]
    
    await state.update_data(
        programs_in_faculty=programs_in_faculty, 
        selected_faculty_index=faculty_index
    )
    await state.set_state(Universities.choosing_program)
    
    await callback.message.edit_text(
        f"<b>{selected_faculty_name}</b>\n\nВыберите программу обучения:",
        reply_markup=get_paginated_keyboard(
            items=program_names, page=0, data_prefix="program", back_callback="back_to_faculties", lexicon=lexicon, lang=lang
        )
    )
    await callback.answer()

@router.callback_query(Universities.choosing_program, F.data.startswith("program_"))
async def program_selected_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    program_index = int(callback.data.split('_')[1])
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    program = user_data.get("programs_in_faculty", [])[program_index]
    
    if not program:
        await callback.answer("Не удалось найти информацию о программе.", show_alert=True)
        return

    await state.set_state(Universities.viewing_faculty) 
    
    card_parts = [f"<b>{program.get('Название программы')}</b>\n"]
    for field_name in VISIBLE_PROGRAM_FIELDS:
        if field_name == "Название программы": continue 
        value = program.get(field_name)
        if value: 
            card_parts.append(f"<b>{field_name}:</b> {value}")
            
    card_text = "\n".join(card_parts)
    
    builder = InlineKeyboardBuilder()
    if program.get("Список документов"):
        builder.row(types.InlineKeyboardButton(text="📄 Список документов", callback_data=f"show_docs_{program_index}"))

    builder.row(types.InlineKeyboardButton(text=lexicon[lang]['button-back'], callback_data="back_to_faculties"))
    
    await callback.message.edit_text(card_text, reply_markup=builder.as_markup())
    await callback.answer()

# --- ОБРАБОТЧИКИ "НАЗАД" ---

@router.callback_query(F.data == "back_to_cities")
async def back_to_cities_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(Universities.choosing_city)
    await callback.message.edit_text(
        "Выберите город:", 
        reply_markup=get_cities_keyboard(lexicon, lang)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_uni_type")
async def back_to_uni_type_handler(
    callback: types.CallbackQuery, 
    state: FSMContext, 
    lexicon: dict, 
):

    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    selected_city = user_data.get("selected_city")

    await state.set_state(Universities.choosing_uni_type)
    await callback.message.edit_text(
        f"Вы выбрали город: {selected_city}.\nТеперь выберите тип вуза:",
        reply_markup=get_uni_types_keyboard(lexicon, lang)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_universities")
async def back_to_universities_handler(
    callback: types.CallbackQuery, 
    state: FSMContext, 
    lexicon: dict, 
):

    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    selected_city = user_data.get("selected_city")
    selected_type = user_data.get("uni_type")
    all_universities_in_file = user_data.get("filtered_universities", [])
    
    uni_names = [uni.get("Наименования ВОУ", "N/A") for uni in all_universities_in_file]
    
    await state.set_state(Universities.choosing_university)
    await callback.message.edit_text(
        f"<b>{selected_city} / {selected_type}</b>\n\nВыберите вуз:",
        reply_markup=get_paginated_keyboard(
            items=uni_names, page=0, data_prefix="uni", back_callback="back_to_uni_type", lexicon=lexicon, lang=lang
        )
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_faculties")
async def back_to_faculties_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, universities_manager: UniversitiesGSheet):
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    uni_index = user_data.get("selected_university_index")
    selected_university = user_data.get("filtered_universities", [])[uni_index]
    unique_faculties = user_data.get("unique_faculties", []) 

    await state.set_state(Universities.choosing_faculty)
    await callback.message.edit_text(
        f"<b>{selected_university.get('Наименования ВОУ')}</b>\n\nВыберите факультет:",
        reply_markup=get_paginated_keyboard(
            items=unique_faculties, page=0, data_prefix="faculty", back_callback="back_to_universities", lexicon=lexicon, lang=lang
        )
    )
    await callback.answer()
    
@router.callback_query(F.data == "back_to_programs")
async def back_to_programs_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')

    faculty_index = user_data.get("selected_faculty_index")
    selected_faculty_name = user_data.get("unique_faculties", [])[faculty_index]
    programs_in_faculty = user_data.get("programs_in_faculty", [])
    program_names = [p.get("Название программы", "N/A") for p in programs_in_faculty]

    await state.set_state(Universities.choosing_program)
    await callback.message.edit_text(
        f"<b>{selected_faculty_name}</b>\n\nВыберите программу обучения:",
        reply_markup=get_paginated_keyboard(
            items=program_names, page=0, data_prefix="program", back_callback="back_to_faculties", lexicon=lexicon, lang=lang
        )
    )
    await callback.answer()

# --- ПАГИНАЦИЯ (ОБЩАЯ) ---

@router.callback_query(F.data.startswith("page_"))
async def pagination_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    parts = callback.data.split('_')
    data_prefix = parts[1]
    page = int(parts[2])
    
    await state.update_data(page=page)
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    
    items_list = []
    back_callback = ""
    
    if data_prefix == 'uni':
        items_list = [uni.get("Наименования ВОУ", "N/A") for uni in user_data.get("filtered_universities", [])]
        back_callback = "back_to_uni_type"
    elif data_prefix == 'faculty':
        items_list = user_data.get("unique_faculties", [])
        back_callback = "back_to_universities"
    elif data_prefix == 'program':
        items_list = [p.get("Название программы", "N/A") for p in user_data.get("programs_in_faculty", [])]
        back_callback = "back_to_faculties"
    
    await callback.message.edit_reply_markup(
        reply_markup=get_paginated_keyboard(
            items=items_list, 
            page=page, 
            data_prefix=data_prefix, 
            back_callback=back_callback, 
            lexicon=lexicon, 
            lang=lang
        )
    )
    await callback.answer()


# --- ОБРАБОТЧИК ДОКУМЕНТОВ ---

@router.callback_query(Universities.viewing_faculty, F.data.startswith("show_docs_"))
async def show_documents_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict): 
    try:
        program_index = int(callback.data.split("_", 2)[2])
        user_data = await state.get_data()
        lang = user_data.get('language', 'ru')
        
        program = user_data.get("programs_in_faculty", [])[program_index]
        documents_text = program.get("Список документов")
        
        if documents_text:
            await callback.message.delete()
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(
                text=lexicon[lang]['button-back'], 
                callback_data=f"program_{program_index}" 
            ))
            
            await callback.message.answer(documents_text, reply_markup=builder.as_markup())
            
        else:
            await callback.answer("Для этой программы список документов не указан.", show_alert=True)
            
    except (ValueError, IndexError):
        await callback.answer("Произошла ошибка. Попробуйте заново.", show_alert=True)

    await callback.answer()

@router.callback_query(Universities.viewing_faculty, F.data.startswith("program_"))
async def back_to_program_card_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    await program_selected_handler(callback, state, lexicon)

