from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import BigInteger

from app.states.registration import Support
from app.core.config import SUPPORT_GROUP_ID

router = Router()

# --- 1. Вход в режим чата с поддержкой  ---

@router.message(F.text.in_({"💬 Поддержка", "💬 Qo'llab-quvvatlash"}))
async def start_support_chat_handler(message: types.Message, state: FSMContext, lexicon: dict):
    user_data = await state.get_data()
    if menu_msg_id := user_data.get('main_menu_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, menu_msg_id)
        except Exception:
            pass
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(Support.active_chat)
    
    await message.answer(lexicon[lang].get('support-welcome', 
        "Вы вошли в режим чата с поддержкой. Напишите ваш вопрос, и мы скоро ответим.\n\n"
        "Чтобы выйти из этого режима, отправьте команду /stop"
    ))

# --- 2. Обработка сообщений от пользователя к поддержке ---

@router.message(Support.active_chat, F.text != "/stop")
async def forward_to_support_group_handler(message: types.Message, bot: Bot):
    user_info = (
        f"Новое сообщение от пользователя:\n"
        f"ID: {message.from_user.id}\n"
        f"Username: @{message.from_user.username or 'не указан'}\n"
        f"Имя: {message.from_user.full_name}"
    )
    await bot.send_message(SUPPORT_GROUP_ID, user_info)
    await bot.forward_message(
        chat_id=SUPPORT_GROUP_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    await message.answer("Ваше сообщение отправлено в поддержку. Ожидайте ответа.")


# --- 3. Обработка ответов от поддержки пользователю ---
@router.message(F.chat.id == int(SUPPORT_GROUP_ID), F.reply_to_message)
async def forward_to_user_handler(message: types.Message, bot: Bot):

    if message.reply_to_message.forward_from:
        user_id = message.reply_to_message.forward_from.id
        
        try:
            await bot.send_message(user_id, "Ответ от поддержки:")
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id 
            )
        except Exception as e:
            await message.reply(f"Не удалось отправить ответ пользователю ID {user_id}. Ошибка: {e}")
    else:
        await message.reply("Чтобы ответить пользователю, используйте функцию 'Ответить' на его пересланное сообщение.")


# --- 4. Выход из режима чата ---

@router.message(Support.active_chat, Command("stop"))
async def stop_support_chat_handler(message: types.Message, state: FSMContext, lexicon: dict):
    lang = (await state.get_data()).get('language', 'ru')
    await state.set_state(None) 
    
    await message.answer(lexicon[lang].get('support-goodbye', "Вы вышли из режима чата с поддержкой."))