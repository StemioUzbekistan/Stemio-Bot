from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.states.registration import ProfessionsExplorer 
from app.utils.google_sheets import ProfessionsGSheet
from app.handlers.stem_navigator import PRIMARY_FIELDS, ADDITIONAL_FIELDS

router = Router()

@router.message(F.text.in_({"💼 Профессии"}))
async def professions_start_handler(message: types.Message, state: FSMContext, professions_manager: ProfessionsGSheet):
    await message.delete()
    user_data = await state.get_data()
    if menu_msg_id := user_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass  
    await state.clear() 

    all_professions = professions_manager.get_all_professions()

    if not all_professions:
        await message.answer("Каталог профессий временно недоступен. (Не удалось загрузить данные из листов human, tech и т.д.)")
        return
    all_directions = sorted(list(set(p.get('Направление') for p in all_professions if p.get('Направление'))))
    await state.update_data(all_professions=all_professions, all_directions=all_directions)
    
    builder = InlineKeyboardBuilder()
    for index, direction in enumerate(all_directions):
        builder.row(types.InlineKeyboardButton(
            text=direction,
            callback_data=f"explore_dir_{index}" 
        ))
    
    builder.row(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu"))

    await state.set_state(ProfessionsExplorer.choosing_direction)
    await message.answer(
        "Выберите интересующее вас направление:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(ProfessionsExplorer.choosing_direction, F.data.startswith("explore_dir_"))
async def direction_selected_handler(callback: types.CallbackQuery, state: FSMContext, professions_manager: ProfessionsGSheet):
    direction_index = int(callback.data.replace("explore_dir_", ""))
    
    user_data = await state.get_data()
    selected_direction = user_data.get('all_directions', [])[direction_index]
    all_professions = user_data.get('all_professions', [])
    filtered_professions = [p for p in all_professions if p.get('Направление') == selected_direction]
    
    builder = InlineKeyboardBuilder()
    for index, prof in enumerate(filtered_professions):
        builder.row(types.InlineKeyboardButton(
            text=prof.get('Название профессии'),
            callback_data=f"explore_prof_{index}"
        ))
    
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к направлениям", callback_data="back_to_directions_list"))
    
    await state.set_state(ProfessionsExplorer.choosing_profession)
    await state.update_data(filtered_professions=filtered_professions)
    
    await callback.message.edit_text(
        f"<b>{selected_direction}</b>\n\nВыберите профессию:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(
    F.data.startswith("explore_prof_"),
    ProfessionsExplorer.choosing_profession, 
    ProfessionsExplorer.viewing_profession   
)
async def show_profession_card_handler(callback: types.CallbackQuery, state: FSMContext):
    prof_index = int(callback.data.replace("explore_prof_", ""))
    user_data = await state.get_data()
    filtered_professions = user_data.get('filtered_professions', [])
    if not filtered_professions or prof_index >= len(filtered_professions):
        await callback.answer("Произошла ошибка, попробуйте заново.", show_alert=True)
        return
        
    profession = filtered_professions[prof_index]
    
    card_text = f"<b>{profession.get('Название профессии')}</b>\n\n"
    for field in PRIMARY_FIELDS:
        if value := profession.get(field):
            card_text += f"<b>{field}:</b> {value}\n"
            
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="📄 Доп. информация", 
        callback_data=f"explore_full_{prof_index}"
    ))
    
    all_directions = user_data.get('all_directions', [])
    direction_name = profession.get('Направление')
    direction_index = all_directions.index(direction_name) if direction_name in all_directions else -1

    builder.row(types.InlineKeyboardButton(
        text="⬅️ Назад к профессиям", 
        callback_data=f"explore_dir_{direction_index}"
    ))
    await state.set_state(ProfessionsExplorer.viewing_profession)
    await callback.message.edit_text(card_text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(ProfessionsExplorer.viewing_profession, F.data.startswith("explore_full_"))
async def show_full_profession_card_handler(callback: types.CallbackQuery, state: FSMContext):
    prof_index = int(callback.data.replace("explore_full_", ""))
    user_data = await state.get_data()
    filtered_professions = user_data.get('filtered_professions', [])
    if not filtered_professions or prof_index >= len(filtered_professions):
        await callback.answer("Произошла ошибка, попробуйте заново.", show_alert=True)
        return

    profession = filtered_professions[prof_index]

    card_text = f"<b>{profession.get('Название профессии')}</b>\n\n"
    all_fields = PRIMARY_FIELDS + ADDITIONAL_FIELDS
    for field in all_fields:
        if value := profession.get(field):
            card_text += f"<b>{field}:</b> {value}\n\n"

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="🔼 Скрыть доп. информацию",
        callback_data=f"explore_prof_{prof_index}" 
    ))
    
    await callback.message.edit_text(card_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# --- ОБРАБОТЧИК КНОПКИ "НАЗАД" к списку направлений ---

@router.callback_query(F.data == "back_to_directions_list")
async def back_to_directions_list_handler(callback: types.CallbackQuery, state: FSMContext, professions_manager: ProfessionsGSheet):
    await state.clear()
    all_professions = professions_manager.get_all_professions()

    all_directions = sorted(list(set(p.get('Направление') for p in all_professions if p.get('Направление'))))
    await state.update_data(all_professions=all_professions, all_directions=all_directions) 
    
    builder = InlineKeyboardBuilder()
    for index, direction in enumerate(all_directions):
        builder.row(types.InlineKeyboardButton(
            text=direction,
            callback_data=f"explore_dir_{index}"
        ))
    
    builder.row(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu"))

    await state.set_state(ProfessionsExplorer.choosing_direction)
    await callback.message.edit_text(
        "Выберите интересующее вас направление:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

