import collections
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.states.registration import StemNavigator
from app.utils.google_sheets import ProfessionsGSheet
from app.utils.test_content import QUESTIONS, SCORING_KEY, SCALES_INFO

router = Router()

# ---  СПИСКИ ПОЛЕЙ  ---
PRIMARY_FIELDS = [
    "О чём профессия?",
    "Чем занимаются?",
    "Какими качествами нужно обладать",
    "Где учиться",
    "Факультеты"
]
ADDITIONAL_FIELDS = [
    "Живые примеры",
    "Где можно работать",
    "Сколько зарабатывают",
    "Перспективы",
    "Смежные профессии",
    "Карьерный рост",
    "Рабочая обстановка",
    "Трудности",
    "Знаменитые представители профессии"
]


# --- ХЕЛПЕРЫ ---

def calculate_results(answers: list[str]) -> list[tuple[str, int]]:
    """Подсчитывает результаты теста."""
    scores = collections.defaultdict(int)
    for answer in answers:
        for scale, keys in SCORING_KEY.items():
            if answer in keys:
                scores[scale] += 1
    
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return sorted_scores[:3]


def get_about_test_keyboard(lexicon: dict, lang: str):
    """Возвращает клавиатуру для экрана 'О тесте'."""
    kb_lang = lexicon.get(lang, {})
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text=kb_lang.get('button-start-test', '📝 Пройти тест'),
        callback_data="begin_stem_test"
    ))
    builder.row(types.InlineKeyboardButton(
        text=kb_lang.get('button-main-menu', '🏠 Главное меню'),
        callback_data="back_to_main_menu"
    ))
    return builder.as_markup()


async def show_test_results(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    user_data = await state.get_data()
    lang = (await state.get_data()).get('language', 'ru')
    top_3_results = user_data.get("test_results") 

    if not top_3_results:
        answers = user_data.get("answers", [])
        if not answers:
            await callback.message.edit_text("Не удалось найти результаты теста. Попробуйте пройти его заново.")
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data="begin_stem_test"))
            await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
            return
            
        top_3_results = calculate_results(answers)
        await state.update_data(test_results=top_3_results) 

    # --- БЛОК СБОРКИ ТЕКСТА ---

    result_text = lexicon[lang].get('test_result_title', "🌟 <b>Вот твой результат:</b>\n\n")
    
    emojis = ["🥇 1 место:", "🥈 2 место:", "🥉 3 место:"]
    result_builder = InlineKeyboardBuilder()
    
    for i, (scale_key, score) in enumerate(top_3_results):
        scale_info = SCALES_INFO[scale_key] 
        scale_description = scale_info['description']
        
        result_text += f"{emojis[i]} <b>{scale_info['title']}</b>\n"
        result_text += f"{scale_description}\n\n" 
        
        result_builder.row(types.InlineKeyboardButton(
            text=f"Посмотреть профессии: {scale_info['title']}",
            callback_data=f"view_directions_{scale_key}" 
        ))
    
    result_text += lexicon[lang].get('test_result_footer', "") # <-- ВОТ ОН

    result_builder.row(types.InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data="begin_stem_test"))
    result_builder.row(types.InlineKeyboardButton(
        text=lexicon[lang].get('button-main-menu', '🏠 Главное меню'), 
        callback_data="back_to_main_menu"
    ))
    
    await callback.message.edit_text(result_text, reply_markup=result_builder.as_markup())
    await state.set_state(StemNavigator.viewing_results)
    


# --- ОБРАБОТЧИКИ ТЕСТА ---

@router.callback_query(F.data == "begin_stem_test")
async def start_test_handler(callback: types.CallbackQuery, state: FSMContext):
    """Начинает тест (вопрос 1)."""
    try:
        await callback.message.delete()
    except Exception:
        pass

    await state.set_state(StemNavigator.taking_test)
    await state.update_data(question_index=0, answers=[], test_results=None)
    
    question = QUESTIONS[0]
    builder = InlineKeyboardBuilder()
    for answer in question["answers"]:
        builder.add(types.InlineKeyboardButton(text=answer["text"], callback_data=answer["data"]))
    builder.adjust(1)

    await callback.message.answer(question["text"], reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(StemNavigator.taking_test)
async def answer_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """Обрабатывает ответ на вопрос и показывает следующий или результат."""
    user_data = await state.get_data()
    answers = user_data.get("answers", [])
    answers.append(callback.data)
    
    question_index = user_data.get("question_index", 0) + 1
    await state.update_data(question_index=question_index, answers=answers)
    
    if question_index < len(QUESTIONS):
        question = QUESTIONS[question_index]
        builder = InlineKeyboardBuilder()
        for answer in question["answers"]:
            builder.add(types.InlineKeyboardButton(text=answer["text"], callback_data=answer["data"]))
        builder.adjust(1)
        await callback.message.edit_text(question["text"], reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text("⏳ Спасибо за ответы! Подсчитываю результаты...")
        await show_test_results(callback, state, lexicon)

    await callback.answer()


# --- ЛОГИКА НАВИГАЦИИ ПО ПРОФЕССИЯМ ---

@router.callback_query(StemNavigator.viewing_results, F.data.startswith("view_directions_"))
async def view_directions_handler(callback: types.CallbackQuery, state: FSMContext, professions_manager: ProfessionsGSheet):
    """Показывает 'Направления' (e.g. 'Медицинское') для выбранной шкалы (e.g. 'human')."""
    scale_key = callback.data.replace("view_directions_", "")

    professions = professions_manager.get_professions_by_scale(scale_key)
    
    if not professions:
        await callback.answer("Профессии для этого направления скоро будут добавлены.", show_alert=True)
        return

    directions = sorted(list(set(prof.get('Направление') for prof in professions if prof.get('Направление'))))

    await state.update_data(
        current_scale_key=scale_key,
        current_directions=directions,
        current_scale_professions=professions 
    )
    
    builder = InlineKeyboardBuilder()
    for index, direction in enumerate(directions):
        builder.row(types.InlineKeyboardButton(text=direction, callback_data=f"view_profs_{index}"))
    
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к результатам", callback_data="back_to_results"))
    
    await callback.message.edit_text(
        f"<b>{SCALES_INFO[scale_key]['title']}</b>\n\nВыберите направление:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(StemNavigator.viewing_results, F.data.startswith("view_profs_"))
async def view_professions_handler(callback: types.CallbackQuery, state: FSMContext, professions_manager: ProfessionsGSheet):
    """Показывает список профессий (e.g. 'Врач') для выбранного направления."""
    direction_index = int(callback.data.replace("view_profs_", ""))

    user_data = await state.get_data()
    directions = user_data.get('current_directions', [])
    direction = directions[direction_index]
    
    all_professions_in_scale = user_data.get('current_scale_professions', [])
    scale_key = user_data.get('current_scale_key')
    
    filtered_professions = [prof for prof in all_professions_in_scale if prof.get('Направление') == direction]
    
    await state.update_data(current_filtered_professions=filtered_professions)

    builder = InlineKeyboardBuilder()
    for index, prof in enumerate(filtered_professions):
        builder.row(types.InlineKeyboardButton(
            text=prof.get('Название профессии'),
            callback_data=f"show_prof_{index}" 
        ))
    
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к направлениям", callback_data=f"view_directions_{scale_key}"))
    
    await callback.message.edit_text(
        f"<b>{direction}</b>\n\nВыберите профессию:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(
    F.data.startswith("show_prof_"),
    StemNavigator.viewing_results 
)
async def show_profession_card_handler(callback: types.CallbackQuery, state: FSMContext):
    """Показывает КОРОТКУЮ карточку профессии."""
    prof_index = int(callback.data.replace("show_prof_", ""))

    user_data = await state.get_data()

    filtered_professions = user_data.get('current_filtered_professions', [])

    if not filtered_professions or prof_index >= len(filtered_professions):
        await callback.answer("Произошла ошибка, пожалуйста, вернитесь назад.", show_alert=True)

        await show_test_results(callback, state, lexicon=await state.get_data().get('lexicon', {}))
        return
        
    profession = filtered_professions[prof_index]
    
    direction = profession.get('Направление')
    directions = user_data.get('current_directions', [])
    direction_index = directions.index(direction) if direction in directions else 0

    card_text = f"<b>{profession.get('Название профессии')}</b>\n\n"
    for field in PRIMARY_FIELDS:
        if value := profession.get(field):
            card_text += f"<b>{field}:</b> {value}\n"
            
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="📄 Доп. информация", 
        callback_data=f"show_full_{prof_index}" 
    ))
    builder.row(types.InlineKeyboardButton(
        text="⬅️ Назад к профессиям", 
        callback_data=f"view_profs_{direction_index}" 
    ))
    
    await state.set_state(StemNavigator.viewing_results) 
    await callback.message.edit_text(card_text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(StemNavigator.viewing_results, F.data.startswith("show_full_"))
async def show_full_profession_card_handler(callback: types.CallbackQuery, state: FSMContext):
    """Показывает ПОЛНУЮ карточку профессии."""
    prof_index = int(callback.data.replace("show_full_", ""))
    
    user_data = await state.get_data()
    filtered_professions = user_data.get('current_filtered_professions', [])

    if not filtered_professions or prof_index >= len(filtered_professions):
        await callback.answer("Произошла ошибка, пожалуйста, вернитесь назад.", show_alert=True)

        await show_test_results(callback, state, lexicon=await state.get_data().get('lexicon', {}))
        return
        
    profession = filtered_professions[prof_index]

    direction = profession.get('Направление')
    directions = user_data.get('current_directions', [])
    direction_index = directions.index(direction) if direction in directions else 0

    card_text = f"<b>{profession.get('Название профессии')}</b>\n\n"
    all_fields = PRIMARY_FIELDS + ADDITIONAL_FIELDS
    for field in all_fields:
        if value := profession.get(field):
            card_text += f"<b>{field}:</b> {value}\n\n"

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="🔼 Скрыть доп. информацию",
        callback_data=f"show_prof_{prof_index}" 
    ))
    builder.row(types.InlineKeyboardButton(
        text="⬅️ Назад к профессиям", 
        callback_data=f"view_profs_{direction_index}"
    ))

    await callback.message.edit_text(card_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(StemNavigator.viewing_results, F.data == "back_to_results")
async def back_to_results_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """Возврат к экрану результатов теста."""
    await show_test_results(callback, state, lexicon)
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

