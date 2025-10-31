from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.states.registration import ParentActions, StemNavigator
from app.utils.google_sheets import RegistrationGSheet
from app.keyboards.inline import get_about_test_keyboard
from app.keyboards.inline import get_parent_start_test_keyboard 
from app.handlers.stem_navigator import show_test_results

router = Router()

def get_children_keyboard(children: list, lexicon: dict, lang: str):
    """Создает клавиатуру со списком детей для выбора."""
    builder = InlineKeyboardBuilder()
    for child in children:
        child_name = child.get('Имя ребенка', 'Имя не указано')

        builder.row(types.InlineKeyboardButton(
            text=child_name,
            callback_data=f"select_child_{child_name}"
        ))
    builder.row(types.InlineKeyboardButton(
        text=lexicon[lang]['button-back'], 
        callback_data="back_to_main_menu" 
    ))
    return builder.as_markup()


@router.callback_query(F.data == "parent_start_test_selection")
async def select_child_for_test_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict, registration_manager: RegistrationGSheet):
    """
    Шаг 1: Запускается после нажатия на 'Пройти тест' в меню родителя.
    Показывает список детей для выбора.
    """
    lang = (await state.get_data()).get('language', 'ru')
    children = registration_manager.get_children_by_parent_id(callback.from_user.id)

    if not children:
        await callback.answer("У вас еще нет добавленных детей. Сначала добавьте ребенка в профиле.", show_alert=True)
        return

    await state.set_state(ParentActions.choosing_child_for_test)
    await callback.message.edit_text(
        text="Выберите, кто из детей будет проходить тест:",
        reply_markup=get_children_keyboard(children, lexicon, lang)
    )
    await callback.answer()


@router.callback_query(ParentActions.choosing_child_for_test, F.data.startswith("select_child_"))
async def start_test_for_child_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    """
    Шаг 2: Запускается после выбора ребенка.
    Показывает инструкцию к тесту и кнопку 'Начать'.
    """
    child_name = callback.data.split('_', 2)[2]
    await state.update_data(test_for_child=child_name)
    
    lang = (await state.get_data()).get('language', 'ru')
    
    await state.set_state(StemNavigator.showing_test_info)

    parent_test_intro = lexicon[lang]['parent-about-test-text'].format(child_name=child_name)
    
    await callback.message.edit_text(
        text=parent_test_intro,
        reply_markup=get_about_test_keyboard(lexicon, lang) 
    )
    await callback.answer()

@router.message(F.text.in_({"🧭 STEM-навигатор", "🧭 STEM-navigator"}))
async def parent_stem_navigator_start(message: types.Message, state: FSMContext, lexicon: dict):

    await message.delete()
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')

    if user_data.get("test_results"):
       
        mock_callback_message = await message.answer("Загружаю ваши предыдущие результаты...")
        mock_callback = types.CallbackQuery(
            id="mock_callback_id", from_user=message.from_user, chat_instance="",
            message=mock_callback_message, data="show_results"
        )
        await show_test_results(mock_callback, state, lexicon)
        
    else:
        intro_text = "Ваш ребенок может пройти тест по профориентации, чтобы определить свои сильные стороны и получить рекомендации по подходящим профессиям и направлениям для учёбы."
        await message.answer(
            text=intro_text,
            reply_markup=get_parent_start_test_keyboard(lexicon, lang)
        )