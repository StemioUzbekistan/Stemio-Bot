from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

# --- Импорты ---
from app.keyboards.inline import get_about_test_keyboard
from app.keyboards.reply import get_parent_main_menu_keyboard, get_student_main_menu_keyboard

router = Router()


@router.callback_query(F.data == "student_start_test_info")
async def action_start_test_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    await callback.message.edit_text(
        text=lexicon[lang]['about-test-text'],
        reply_markup=get_about_test_keyboard(lexicon, lang)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("action_") | (F.data == "back_to_main_menu"))
async def section_callback_handler(callback: types.CallbackQuery, state: FSMContext, lexicon: dict):
    user_data = await state.get_data()
    lang = user_data.get('language', 'ru')
    role = user_data.get('role') 

    if callback.data == "back_to_main_menu":
        await callback.message.delete()

        is_parent = role == 'parent'

        menu_message = await callback.message.answer(
            text=lexicon[lang]['main-menu-welcome'],
            reply_markup=get_parent_main_menu_keyboard(lexicon, lang) if is_parent else get_student_main_menu_keyboard(lexicon, lang)
        )
        await state.update_data(main_menu_message_id=menu_message.message_id)
        
        await callback.answer()
    else:

        await callback.answer(lexicon[lang]['coming-soon'], show_alert=True)
