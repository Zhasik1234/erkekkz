
import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    TelegramObject
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

# Импортируем функции базы данных
from database import get_banned_users, ban_user_id, unban_user_id, add_purchase, get_recent_purchases

# === ЗАГРУЗКА НАСТРОЕК ИЗ config.env ===
load_dotenv("config.env")

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CARD_REQUISITES = os.getenv("CARD_REQUISITES", "").replace("\\n", "\n")

link_vip = os.getenv("LINK_VIP")
link_premium = os.getenv("LINK_PREMIUM")

SUBSCRIPTION_LINKS = {
    "VIP": link_vip,
    "PREMIUM": link_premium,
    "VIP+PREMIUM": f"VIP: {link_vip}\nPREMIUM: {link_premium}",
    "ULTRA": f"VIP: {link_vip}\nPREMIUM: {link_premium}"
}
# =======================================

router = Router()

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        
        # Запрашиваем список банов из БД
        banned_users = await get_banned_users()
        
        if user and user.id in banned_users:
            state: FSMContext = data.get("state")
            if state:
                await state.clear()
                
            if isinstance(event, Message):
                await event.answer("❌ <b>Доступ ограничен.</b>\nВы заблокированы администратором.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Доступ ограничен. Вы заблокированы.", show_alert=True)
                
            return 
            
        return await handler(event, data)

router.message.outer_middleware(BanCheckMiddleware())
router.callback_query.outer_middleware(BanCheckMiddleware())

class BotStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_receipt = State()
    admin_waiting_ban = State()
    admin_waiting_unban = State()

main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 VIP Подписка", callback_data="sub_VIP")],
    [InlineKeyboardButton(text="👑 PREMIUM Подписка", callback_data="sub_PREMIUM")],
    [InlineKeyboardButton(text="💎+👑 ВИП+PREMIUM Подписка", callback_data="sub_VIP+PREMIUM")],
    [InlineKeyboardButton(text="🚀 ULTRA Подписка", callback_data="sub_ULTRA")],
    [InlineKeyboardButton(text="🆘 Помощь админа\n\n🆘 Админнан комек", callback_data="admin_help")]
])

# Обновленная клавиатура админа (добавлена кнопка покупок)
admin_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚫 Заблокировать по ID", callback_data="admin_ban")],
    [InlineKeyboardButton(text="🟢 Разблокировать по ID", callback_data="admin_unban")],
    [InlineKeyboardButton(text="📋 Список заблокированных", callback_data="admin_list")],
    [InlineKeyboardButton(text="💰 Последние покупки", callback_data="admin_stats")]
])

# ================= ХЭНДЛЕРЫ АДМИН-ПАНЕЛИ =================

@router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def open_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🛠 <b>Добро пожаловать в панель администратора:</b>", reply_markup=admin_kb, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "admin_ban", F.from_user.id == ADMIN_ID)
async def admin_ban_click(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Введите Telegram ID пользователя, которого нужно заблокировать:")
    await state.set_state(BotStates.admin_waiting_ban)
    await callback.answer()

@router.message(BotStates.admin_waiting_ban, F.from_user.id == ADMIN_ID)
async def process_ban_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ ID должен состоять только из цифр. Попробуйте еще раз:")
        return
        
    target_id = int(message.text)
    if target_id == ADMIN_ID:
        await message.answer("❌ Вы не можете заблокировать самого себя!")
        await state.clear()
        return

    await ban_user_id(target_id)
    await message.answer(f"✅ Пользователь с ID <code>{target_id}</code> успешно <b>заблокирован</b>.", parse_mode=ParseMode.HTML)
    await state.clear()

@router.callback_query(F.data == "admin_unban", F.from_user.id == ADMIN_ID)
async def admin_unban_click(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Введите Telegram ID пользователя для разблокировки:")
    await state.set_state(BotStates.admin_waiting_unban)
    await callback.answer()

@router.message(BotStates.admin_waiting_unban, F.from_user.id == ADMIN_ID)
async def process_unban_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ ID должен состоять только из цифр. Попробуйте еще раз:")
        return
        
    target_id = int(message.text)
    await unban_user_id(target_id)
    await message.answer(f"🟢 Пользователь с ID <code>{target_id}</code> успешно <b>разблокирован</b>.", parse_mode=ParseMode.HTML)
    await state.clear()

@router.callback_query(F.data == "admin_list", F.from_user.id == ADMIN_ID)
async def admin_list_click(callback: CallbackQuery):
    banned = await get_banned_users()
    if not banned:
        await callback.message.answer("📋 Список заблокированных пуст.")
    else:
        text = "📋 <b>Список заблокированных ID:</b>\n\n"
        for uid in banned:
            text += f"• <code>{uid}</code>\n"
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

# Кнопка статистики покупок
@router.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def admin_stats_click(callback: CallbackQuery):
    purchases = await get_recent_purchases(10)
    
    if not purchases:
        await callback.message.answer("🤷‍♂️ Пока никто ничего не купил.")
    else:
        text = "💰 <b>Последние 10 покупок:</b>\n\n"
        for p in purchases:
            uid, uname, sub, p_date = p
            text += f"• {p_date} | {uname} (<code>{uid}</code>)\n  └ Тариф: <b>{sub}</b>\n\n"
            
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()
    
@router.message(Command("del_pay"), F.from_user.id == ADMIN_ID)
async def delete_purchase(message: Message):
    # Разделим сообщение, чтобы получить ID покупки: /del_pay 5
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Используй: /del_pay <ID_покупки>")
        return
    
    pay_id = args[1]
    
    import aiosqlite
    async with aiosqlite.connect("bot.db") as db:
        await db.execute('DELETE FROM purchases WHERE id = ?', (pay_id,))
        await db.commit()
        
    await message.answer(f"✅ Покупка с ID {pay_id} удалена из базы.")

# ================= ХЭНДЛЕРЫ ПОЛЬЗОВАТЕЛЕЙ =================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    prices_text = (
        f"Салем, {message.from_user.first_name}!\n\n"
        "💎 <b>VIP Подписка</b>\n"
        "<i>⭐️VIP канал - <s>1500</s> 1000тг, ішінде 200 шақты қазақша порнография, қысқа қысқа видеолар, сабина, мадина секілді блогерлармен сливтер🫦</i>\n\n"
        "👑 <b>PREMIUM Подписка</b>\n"
        "<i>👑PREMIUM - <s>3000</s> 2000тг, ішінде барлық жаңа видеолар, сливтар. Руфаши, Алмира, Айым, Закладчица, Олжасхан, Дарикорн, Баянсұлудың әпшесі, Мереке және т.б. блогерлердің сливтері және қазақша видеолар. Тек сапалы, ұзақ, жаңа видеолар❤️‍🔥</i>\n\n"
        "🚀 <b>ULTRA Подписка</b>\n"
        "<i>🤍ULTRA - <s>12900</s> 4500тг, ішінде БҮКІЛ тик токтағы танымал болып жатқан блогерлердің сливтары, кез келген форматтағы видеолар, менің жеке салып тұратын видео-фотоларым, күнделікті жаңа видеолар💎. ULTRA каналын алғандарға VIP+PREMIUM в подарок⭐️.</i>\n\n"
        "🙃СКИДКАМЕН ВИП+PREMIUM — <s>4500</s> 2500ТГ!"
    )
    await message.answer(prices_text, parse_mode=ParseMode.HTML)
    await message.answer(
        "👇 Выберите нужный тариф для оплаты👇\nКандай тариф кажет:", 
        reply_markup=main_kb
    )

@router.callback_query(F.data.startswith("sub_"))
async def send_requisites(callback: CallbackQuery, state: FSMContext):
    sub_type = callback.data.split("_")[1] 
    await state.update_data(selected_sub=sub_type)
    
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        f"Тариф: <b>{sub_type}</b>\n\n{CARD_REQUISITES}\n\n"
        "🧾 <b>После оплаты отправьте сюда PDF-файл с чеком.</b>\nЯ передам его администратору на проверку.\n\n"
        "🧾 <b>Толегеннен кейын осында PDF-файл чекты жберыныз.</b>\nМен оны админдарга жберемын.",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(BotStates.waiting_for_receipt)
    await callback.answer()

@router.message(BotStates.waiting_for_receipt, F.document)
async def handle_receipt(message: Message, state: FSMContext, bot: Bot):
    if message.document.mime_type != 'application/pdf':
        await message.answer("⚠️ Пожалуйста, отправьте чек именно в формате PDF.\n\n⚠️ Отыныш, чекты PDF форматта жберу")
        return

    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    document_id = message.document.file_id
    
    data = await state.get_data()
    sub_type = data.get("selected_sub", "Неизвестно")
    
    admin_pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"pay_approve:{user_id}:{sub_type}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"pay_reject:{user_id}")
        ]
    ])
    
    await bot.send_document(
        chat_id=ADMIN_ID,
        document=document_id,
        caption=f"💰 <b>Новая оплата!</b>\nТариф: <b>{sub_type}</b>\nОт: @{user_name} (ID: <code>{user_id}</code>)",
        reply_markup=admin_pay_kb,
        parse_mode=ParseMode.HTML
    )
    await message.answer("⏳ Чек отправлен администратору. Ожидайте ссылку!\n\n⏳ Чек админдарга жберылды. Ссылканы кутыныз!")
    await state.clear()

@router.message(BotStates.waiting_for_receipt)
async def handle_receipt_wrong_format(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте чек именно в формате PDF.")

@router.callback_query(F.data.startswith("pay_approve:"))
async def process_payment_approve(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    user_id = int(parts[1])
    sub_type = parts[2]
    
    link = SUBSCRIPTION_LINKS.get(sub_type, "Ссылка не найдена")

    # Сохраняем покупку в базу данных
    try:
        chat = await bot.get_chat(user_id)
        username = f"@{chat.username}" if chat.username else chat.first_name
    except Exception:
        username = "Неизвестно"
    
    await add_purchase(user_id, username, sub_type)

    success_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆘 Связь с админом", callback_data="admin_help")]
    ])
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 <b>Оплата тарифа {sub_type} подтверждена!</b>\n\nВаша персональная ссылка для входа:\n{link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=success_kb
        )
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n🟢 <b>Одобрено! Ссылка на {sub_type} отправлена.</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка отправки: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("pay_reject:"))
async def process_payment_reject(callback: CallbackQuery, bot: Bot):
    user_id = int(callback.data.split(":")[1])
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ <b>Ваша оплата была отклонена администратором.</b>",
            parse_mode=ParseMode.HTML
        )
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n🔴 <b>Оплата отклонена.</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка отправки: {e}")
    await callback.answer()

@router.callback_query(F.data == "admin_help")
async def ask_admin_help(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer("✍️ Напишите ваш вопрос одним сообщением, и я передам его администратору:")
    await state.set_state(BotStates.waiting_for_question)
    await callback.answer()

@router.message(BotStates.waiting_for_question, F.text)
async def forward_to_admin(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    banned_users = await get_banned_users()
    
    if user_id in banned_users:
        await state.clear()
        return
        
    user_name = message.from_user.username or message.from_user.first_name
    admin_text = f"🚨 <b>Новое обращение!</b>\nОт: @{user_name} (ID: <code>{user_id}</code>)\n\n<b>Текст:</b> {message.text}\n\n<i>⚠️ Чтобы ответить, сделай Reply.</i>"
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode=ParseMode.HTML)
        await message.answer("✅ Ваш вопрос успешно отправлен! Ожидайте ответа.")
    except Exception:
        await message.answer("❌ Ошибка отправки сообщения.")
    await state.clear()

@router.message(F.reply_to_message & (F.from_user.id == ADMIN_ID))
async def admin_reply_handler(message: Message, bot: Bot):
    original_text = message.reply_to_message.text
    if not original_text or "Новое обращение!" not in original_text:
        return
    try:
        user_id_str = original_text.split("(ID: ")[1].split(")")[0]
        user_id = int(user_id_str)
        await bot.send_message(chat_id=user_id, text=f"👨‍💻 <b>Ответ от администратора:</b>\n\n{message.text}", parse_mode=ParseMode.HTML)
        await message.reply("✅ Ответ успешно отправлен!")
    except Exception:
        await message.reply("❌ Не удалось отправить ответ.")





