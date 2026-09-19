import asyncio
import logging
import datetime
import aiohttp

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ==========================================
# НАСТРОЙКИ
# ==========================================
BOT_TOKEN = "8584595054:AAFaOCkFMj-ubDoUVvktZha9-cxkIs3C_5g"
ADMIN_ID = 6442757600

# API ТОКЕНЫ
CRYPTOBOT_API_KEY = "636361:AAN4Sq8seBXAknMNzzmYHOmOIAxvDZpfFOz"
XROCKET_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBJZCI6IjMwMjE5NSIsImp0aSI6ImFwcDozMDIxOTU6NTI3Y2VkZjktZDMwZS00NTdiLTlkMzUtYzA3N2VjMWIwMWI5IiwiaWF0IjoxNzg5ODM4ODQ3fQ.13YcOQAYir8ypmCi5PN_SAKTOfGhQPLBfl3KpFy0CbI"

# ⚠️ ВАЖНО: Замените на реальный username вашего бота (без @)
BOT_USERNAME = "repold_bot" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# БАЗА ДАННЫХ (ВРЕМЕННАЯ)
# ==========================================
users_db = {}
deals_db = {}
deal_counter = 1

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"balance": 0.0, "username": "User"}
    return users_db[user_id]

# ==========================================
# СОСТОЯНИЯ (FSM)
# ==========================================
class DealCreationStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_amount = State()
    waiting_for_description = State()
    confirmation = State()

class TopupStates(StatesGroup):
    waiting_for_crypto_amount = State()
    waiting_for_xrocket_amount = State()

class SearchStates(StatesGroup):
    waiting_for_query = State()

# ==========================================
# ТЕКСТЫ СООБЩЕНИЙ
# ==========================================
MAIN_MENU_TEXT = (
    "<blockquote>🛡 <b>Репутация | Автогарант — система репутации и доверия.</b>\n\n"
    "Проверяй пользователей перед сделкой, оставляй отзывы и следи за своей репутацией.</blockquote>"
)

AUTOGARANT_TEXT = (
    "<blockquote>🛡 <b>Автосделки</b>\n\n"
    "Безопасные сделки с гарантией через эскроу.\n"
    "Без комиссии сервиса.</blockquote>"
)

CREATE_DEAL_ROLE_TEXT = (
    "<blockquote>🛡 <b>Создание сделки</b>\n\n"
    "<b>Кем вы выступаете?</b>\n\n"
    "🛒 <b>Покупатель —</b> вы платите и ждёте товар или услугу\n"
    "💼 <b>Продавец —</b> вы передаёте товар или услугу и ждёте оплату</blockquote>"
)

AMOUNT_TEXT = (
    "<blockquote>💵 <b>Введите сумму сделки в USDT</b>\n\n"
    "<b>Минимум:</b> 1 USDT\n"
    "<b>Пример:</b> 50 или 12.5</blockquote>"
)

DESCRIPTION_TEXT = (
    "<blockquote>📝 <b>Опишите условия сделки</b>\n\n"
    "Эти условия увидит ваш партнёр.\n"
    "Пишите чётко — в случае спора арбитраж опирается только на них.\n\n"
    "<b>Можно использовать шаблон:</b>\n"
    "— Что передаётся\n"
    "— В какие сроки\n"
    "— Что считается выполнением\n"
    "— Что считается нарушением</blockquote>"
)

# ==========================================
# КЛАВИАТУРЫ (С ЦВЕТАМИ)
# ==========================================
def main_inline_menu():
    kb = [
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile", style="primary"),
            InlineKeyboardButton(text="🔍 Поиск", callback_data="search", style="primary")
        ],
        [InlineKeyboardButton(text="🛡 АвтоГарант 6%", callback_data="autogarant", style="success")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def profile_menu():
    kb = [
        [InlineKeyboardButton(text="🔥 Репутация", callback_data="rep", style="primary")],
        [InlineKeyboardButton(text="👛 Кошелёк", callback_data="wallet", style="primary")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main", style="danger")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def wallet_menu():
    kb = [
        [
            InlineKeyboardButton(text="➕ Пополнить", callback_data="wallet_deposit", style="success"),
            InlineKeyboardButton(text="➖ Вывести", callback_data="wallet_withdraw", style="danger")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_profile", style="primary")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def topup_methods_menu():
    kb = [
        [
            InlineKeyboardButton(text="💳 CryptoBot", callback_data="topup_cryptobot", style="success"),
            InlineKeyboardButton(text="💳 xRocket", callback_data="topup_xrocket", style="success")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="wallet", style="primary")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def autogarant_menu():
    kb = [
        [
            InlineKeyboardButton(text="👛 Кошелёк", callback_data="wallet", style="primary"),
            InlineKeyboardButton(text="🤝 Мои сделки", callback_data="my_deals", style="primary")
        ],
        [InlineKeyboardButton(text="🔍 Создать сделку", callback_data="create_deal", style="success")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main", style="danger")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def role_menu():
    kb = [
        [InlineKeyboardButton(text="🛒 Покупатель", callback_data="role_buyer", style="success")],
        [InlineKeyboardButton(text="💼 Продавец", callback_data="role_seller", style="danger")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="autogarant", style="primary")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def amount_back_menu():
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="create_deal", style="primary")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def description_back_menu():
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_amount", style="primary")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def confirmation_menu():
    kb = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_deal", style="success"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_deal", style="danger")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def invitation_menu(deal_id):
    partner_link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
    kb = [
        [InlineKeyboardButton(text="🔗 Ссылка для партнёра", url=partner_link, style="primary")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="autogarant", style="danger")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def partner_deal_menu(deal_id):
    kb = [
        [InlineKeyboardButton(text="✅ Подтвердить выполнение", callback_data=f"partner_complete_{deal_id}", style="success")],
        [InlineKeyboardButton(text="⚠️ Открыть спор", callback_data=f"partner_dispute_{deal_id}", style="danger")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main", style="primary")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_menu():
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main", style="primary")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu(deal_id):
    kb = [
        [InlineKeyboardButton(text="✅ Вернуть деньги покупателю", callback_data=f"admin_refund_{deal_id}", style="success")],
        [InlineKeyboardButton(text="✅ Перевести деньги продавцу", callback_data=f"admin_payout_{deal_id}", style="success")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==========================================
# СТАРТ (С ОБРАБОТКОЙ ПЕРЕХОДА ПО ССЫЛКЕ)
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    get_user(message.from_user.id)
    
    if command.args and command.args.startswith("deal_"):
        try:
            deal_id = int(command.args.split("_")[1])
            deal = deals_db.get(deal_id)
            
            if not deal:
                await message.answer("<blockquote>❌ Сделка не найдена или была отменена.</blockquote>", parse_mode="HTML")
                return
            
            if deal["creator_id"] == message.from_user.id:
                await message.answer("<blockquote>⚠️ Вы не можете принять свою же сделку.</blockquote>", parse_mode="HTML")
                return

            if deal["status"] != "waiting_partner":
                await message.answer("<blockquote>⚠️ Эта сделка уже была принята или завершена.</blockquote>", parse_mode="HTML")
                return

            partner_role = "seller" if deal["creator_role"] == "buyer" else "buyer"
            role_emoji = "💼" if partner_role == "seller" else "🛒"
            role_name = "Продавец" if partner_role == "seller" else "Покупатель"
            
            invite_text = (
                f"<blockquote>🔗 <b>Приглашение в сделку #{deal_id}</b>\n\n"
                f"<b>Ваша роль:</b> {role_emoji} {role_name}\n"
                f"<b>Сумма:</b> {deal['amount']:.2f} USDT\n\n"
                "Нажмите кнопку ниже чтобы принять участие.</blockquote>"
            )
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Принять сделку", callback_data=f"accept_invite_{deal_id}", style="success")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main", style="primary")]
            ])
            
            await message.answer(text=invite_text, reply_markup=kb, parse_mode="HTML")
            return
            
        except ValueError:
            pass

    await message.answer(text=MAIN_MENU_TEXT, reply_markup=main_inline_menu(), parse_mode="HTML")

# ==========================================
# ПРИНЯТИЕ СДЕЛКИ ПАРТНЕРОМ (С ПРОВЕРКОЙ БАЛАНСА)
# ==========================================
@dp.callback_query(F.data.startswith("accept_invite_"))
async def accept_invite(callback: types.CallbackQuery):
    deal_id = int(callback.data.split("_")[2])
    deal = deals_db.get(deal_id)
    
    if not deal or deal["status"] != "waiting_partner":
        await callback.answer("Сделка уже неактуальна.", show_alert=True)
        return
    
    user = get_user(callback.from_user.id)
    if user["balance"] < deal["amount"]:
        text = (
            f"<blockquote>❌ <b>Недостаточно средств!</b>\n\n"
            f"Для принятия сделки необходимо <b>{deal['amount']:.2f} USDT</b>.\n"
            f"Ваш баланс: <b>{user['balance']:.2f} USDT</b>.\n\n"
            "Пожалуйста, пополните баланс и попробуйте снова.</blockquote>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Пополнить", callback_data="wallet_deposit", style="success")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main", style="primary")]
        ])
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return
        
    deal["status"] = "in_progress"
    deal["partner_id"] = callback.from_user.id
    
    await callback.message.edit_text(
        "<blockquote>✅ <b>Вы приняли сделку!</b>\n\n"
        "Ожидайте выполнения условий от второй стороны. "
        "Используйте кнопки ниже для управления сделкой.</blockquote>", 
        reply_markup=partner_deal_menu(deal_id),
        parse_mode="HTML"
    )
    
    try:
        await bot.send_message(
            deal["creator_id"],
            f"<blockquote>🎉 <b>Партнёр принял вашу сделку #{deal_id}!</b>\n\n"
            "Теперь вы можете выполнять условия. Следите за статусом в разделе «Мои сделки».</blockquote>",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Failed to notify creator: {e}")
        
    await callback.answer()

# ==========================================
# 👤 ПРОФИЛЬ И КОШЕЛЁК
# ==========================================
@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    username = callback.from_user.username if callback.from_user.username else f"user_{callback.from_user.id}"
    now = datetime.datetime.now()
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", 
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    date_str = f"{now.day} {months[now.month-1]} {now.year} года"
    user = get_user(callback.from_user.id)

    text = (
        f"<blockquote><b>@{username}</b> [ID: {callback.from_user.id}]\n\n"
        "⭐ <b>Репутация:</b> 0 REP\n· 0.0%\n· 0.0%\n\n"
        f"💳 <b>Депозит:</b> ${user['balance']:.2f} [≈ 0 ₽]\n\n"
        "💵 <b>Сделки:</b> 0 шт · $0 [≈ 0 ₽]\n\n"
        "❗ <b>ВНИМАТЕЛЬНО СМОТРИТЕ ПОЛЕ «О СЕБЕ»</b>\n\n"
        f"<b>В системе с {date_str}</b></blockquote>"
    )
    await callback.message.edit_text(text=text, reply_markup=profile_menu(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: types.CallbackQuery):
    await show_profile(callback)

@dp.callback_query(F.data == "wallet")
async def show_wallet(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    text = (
        "<blockquote>👛 <b>Кошелёк</b>\n\n"
        f"💵 <b>Баланс: {user['balance']:.2f} USDT</b>\n\n"
        "➕ <b>Пополнение — от 1 USDT · комиссия 6%</b>\n"
        "➖ <b>Вывод — от 1 USDT · комиссия 0%</b></blockquote>"
    )
    await callback.message.edit_text(text=text, reply_markup=wallet_menu(), parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🛡 АВТОГАРАНТ
# ==========================================
@dp.callback_query(F.data == "autogarant")
async def show_autogarant(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        text=AUTOGARANT_TEXT,
        reply_markup=autogarant_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "create_deal")
async def create_deal_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(DealCreationStates.waiting_for_role)
    await callback.message.edit_text(
        text=CREATE_DEAL_ROLE_TEXT,
        reply_markup=role_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("role_"))
async def process_role(callback: types.CallbackQuery, state: FSMContext):
    role = "buyer" if callback.data == "role_buyer" else "seller"
    await state.update_data(role=role)
    await state.set_state(DealCreationStates.waiting_for_amount)
    await callback.message.edit_text(
        text=AMOUNT_TEXT,
        reply_markup=amount_back_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_amount")
async def back_to_amount(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(DealCreationStates.waiting_for_amount)
    await callback.message.edit_text(
        text=AMOUNT_TEXT,
        reply_markup=amount_back_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(DealCreationStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount < 1.0:
            await message.answer("<blockquote>❌ Минимальная сумма — 1 USDT. Введите сумму заново:</blockquote>", parse_mode="HTML")
            return
    except ValueError:
        await message.answer("<blockquote>❌ Пожалуйста, введите корректное число:</blockquote>", parse_mode="HTML")
        return

    await state.update_data(amount=amount)
    await state.set_state(DealCreationStates.waiting_for_description)
    await message.answer(
        text=DESCRIPTION_TEXT,
        reply_markup=description_back_menu(),
        parse_mode="HTML"
    )

@dp.message(DealCreationStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    description = message.text
    await state.update_data(description=description)
    
    data = await state.get_data()
    role = data.get('role')
    amount = data.get('amount')
    
    role_emoji = "🛒" if role == "buyer" else "💼"
    role_name = "Покупатель" if role == "buyer" else "Продавец"
    
    confirm_text = (
        "<blockquote>✅ <b>Проверьте данные перед созданием</b>\n\n"
        f"👤 <b>Ваша роль:</b> {role_emoji} {role_name}\n"
        f"💵 <b>Сумма сделки:</b> {amount:.2f} USDT\n"
        f"💵 <b>Сумма к оплате:</b> {amount:.2f} USDT\n\n"
        f"📝 <b>Условия:</b>\n\n{description}\n\n"
        "<b>После подтверждения изменить данные нельзя.</b></blockquote>"
    )
    
    await state.set_state(DealCreationStates.confirmation)
    await message.answer(
        text=confirm_text,
        reply_markup=confirmation_menu(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "cancel_deal")
async def cancel_deal(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        text=AUTOGARANT_TEXT,
        reply_markup=autogarant_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "confirm_deal")
async def confirm_deal(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    role = data.get('role')
    amount = data.get('amount')
    description = data.get('description')
    user_id = callback.from_user.id
    
    global deal_counter
    deal_id = deal_counter
    deal_counter += 1
    
    deals_db[deal_id] = {
        "creator_id": user_id,
        "creator_role": role,
        "amount": amount,
        "description": description,
        "status": "waiting_partner"
    }
    
    partner_role = "seller" if role == "buyer" else "buyer"
    partner_emoji = "💼" if partner_role == "seller" else "🛒"
    partner_name = "Продавец" if partner_role == "seller" else "Покупатель"
    
    partner_link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
    
    invite_text = (
        f"<blockquote>🔗 <b>Приглашение в сделку #{deal_id}</b>\n\n"
        f"<b>Ваша роль:</b> {partner_emoji} {partner_name}\n"
        f"<b>Сумма:</b> {amount:.2f} USDT\n\n"
        "Нажмите кнопку ниже чтобы принять участие.\n\n"
        f"<a href='{partner_link}'>👉 Ссылка для партнёра</a></blockquote>"
    )
    
    await state.clear()
    await callback.message.edit_text(
        text=invite_text,
        reply_markup=invitation_menu(deal_id),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()

@dp.callback_query(F.data == "my_deals")
async def my_deals(callback: types.CallbackQuery):
    await callback.answer("Раздел в разработке", show_alert=True)

# ==========================================
# 💳 ПОПОЛНЕНИЕ
# ==========================================
@dp.callback_query(F.data == "wallet_deposit")
async def wallet_deposit(callback: types.CallbackQuery):
    text = "<blockquote>💵 <b>Выберите способ пополнения</b></blockquote>"
    await callback.message.edit_text(text=text, reply_markup=topup_methods_menu(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "topup_cryptobot")
async def topup_cryptobot(callback: types.CallbackQuery, state: FSMContext):
    text = "<blockquote>💳 <b>Пополнение через CryptoBot</b>\n\nВведите сумму в USDT (минимум 1):</blockquote>"
    await callback.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="wallet_deposit", style="danger")]]),
        parse_mode="HTML"
    )
    await state.set_state(TopupStates.waiting_for_crypto_amount)
    await callback.answer()

@dp.message(TopupStates.waiting_for_crypto_amount)
async def process_crypto_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount < 1.0:
            await message.answer("<blockquote>❌ Минимальная сумма — 1 USDT. Введите сумму заново:</blockquote>", parse_mode="HTML")
            return
    except ValueError:
        await message.answer("<blockquote>❌ Пожалуйста, введите число:</blockquote>", parse_mode="HTML")
        return

    await message.answer("<blockquote>⏳ Создаем счет...</blockquote>", parse_mode="HTML")
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_API_KEY, "Content-Type": "application/json"}
    payload = {"asset": "USDT", "amount": str(amount), "description": "Пополнение баланса"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                if data.get("ok"):
                    pay_url = data["result"]["bot_invoice_url"]
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💳 Перейти к оплате", url=pay_url, style="success")],
                        [InlineKeyboardButton(text="⬅️ В кошелёк", callback_data="wallet", style="primary")]
                    ])
                    text = f"<blockquote>✅ <b>Счет на {amount} USDT создан!</b>\nНажмите кнопку ниже для оплаты.</blockquote>"
                    await message.answer(text, reply_markup=kb, parse_mode="HTML")
                else:
                    await message.answer(f"<blockquote>❌ Ошибка API CryptoBot: {data.get('error', {}).get('name')}</blockquote>", parse_mode="HTML")
    except Exception as e:
        logging.error(f"CryptoBot API error: {e}")
        await message.answer("<blockquote>❌ Не удалось связаться с API CryptoBot.</blockquote>", parse_mode="HTML")
    await state.clear()

# --- XROCKET (v2) ---
@dp.callback_query(F.data == "topup_xrocket")
async def topup_xrocket(callback: types.CallbackQuery, state: FSMContext):
    text = "<blockquote>🚀 <b>Пополнение через xRocket</b>\n\nВведите сумму в USDT (минимум 1):</blockquote>"
    await callback.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="wallet_deposit", style="danger")]]),
        parse_mode="HTML"
    )
    await state.set_state(TopupStates.waiting_for_xrocket_amount)
    await callback.answer()

@dp.message(TopupStates.waiting_for_xrocket_amount)
async def process_xrocket_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount < 1.0:
            await message.answer("<blockquote>❌ Минимальная сумма — 1 USDT. Введите сумму заново:</blockquote>", parse_mode="HTML")
            return
    except ValueError:
        await message.answer("<blockquote>❌ Пожалуйста, введите число:</blockquote>", parse_mode="HTML")
        return

    await message.answer("<blockquote>⏳ Создаем счет в xRocket...</blockquote>", parse_mode="HTML")
    
    url = "https://pay.api.xrocket.exchange/api/v1/invoices"
    headers = {
        "Authorization": f"Bearer {XROCKET_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "priceAmount": str(amount),
        "priceCurrency": "USDT",
        "description": "Пополнение баланса в Гарант-Боте",
        "expiresIn": 3600
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    links = data.get("links", {})
                    pay_url = links.get("telegramBotLink") or links.get("webLink")
                    
                    if pay_url:
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🚀 Перейти к оплате", url=pay_url, style="success")],
                            [InlineKeyboardButton(text="⬅️ В кошелёк", callback_data="wallet", style="primary")]
                        ])
                        text = f"<blockquote>✅ <b>Счет на {amount} USDT создан!</b>\nНажмите кнопку ниже для оплаты.</blockquote>"
                        await message.answer(text, reply_markup=kb, parse_mode="HTML")
                    else:
                        await message.answer("<blockquote>⚠️ Ссылка на оплату не найдена в ответе API.</blockquote>", parse_mode="HTML")
                        logging.error(f"xRocket API response (no pay_url): {data}")
                else:
                    error_data = await resp.json()
                    error_msg = error_data.get("message") or error_data.get("detail") or "Неизвестная ошибка"
                    await message.answer(f"<blockquote>❌ Ошибка API xRocket ({resp.status}): {error_msg}</blockquote>", parse_mode="HTML")
                    logging.error(f"xRocket API error ({resp.status}): {error_data}")
    except Exception as e:
        logging.error(f"xRocket API request error: {e}")
        await message.answer("<blockquote>❌ Не удалось связаться с API xRocket.</blockquote>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "wallet_withdraw")
async def wallet_withdraw(callback: types.CallbackQuery):
    text = "<blockquote>🏦 <b>Вывод средств</b>\n\nВведите сумму для вывода (от 1 USDT).\nКомиссия: 0%</blockquote>"
    await callback.message.edit_text(text, reply_markup=wallet_menu(), parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🔍 ПОИСК
# ==========================================
@dp.callback_query(F.data == "search")
async def show_search(callback: types.CallbackQuery, state: FSMContext):
    text = "<blockquote>🔍 <b>Введите @юзернейм или ID пользователя для поиска.</b></blockquote>"
    await callback.message.edit_text(text=text, reply_markup=back_menu(), parse_mode="HTML")
    await state.set_state(SearchStates.waiting_for_query)
    await callback.answer()

@dp.message(SearchStates.waiting_for_query)
async def process_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if query.isdigit():
        user_id = int(query)
        username = "Пользователь"
    else:
        user_id = message.from_user.id
        username = query.replace("@", "")
    
    now = datetime.datetime.now()
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", 
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    date_str = f"{now.day} {months[now.month-1]} {now.year} года"
    
    text = (
        f"<blockquote><b>@{username}</b> [ID: {user_id}]\n\n"
        "⭐ <b>Репутация:</b> 0 REP\n· 0.0%\n· 0.0%\n\n"
        "💳 <b>Депозит:</b> $0.00 [≈ 0 ₽]\n\n"
        "💵 <b>Сделки:</b> 0 шт · $0 [≈ 0 ₽]\n\n"
        "❗ <b>ВНИМАТЕЛЬНО СМОТРИТЕ ПОЛЕ «О СЕБЕ»</b>\n\n"
        f"<b>В системе с {date_str}</b></blockquote>"
    )
    await message.answer(text, reply_markup=profile_menu(), parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "rep")
async def show_rep(callback: types.CallbackQuery):
    text = "<blockquote>🔥 <b>Ваша репутация:</b> 0 REP</blockquote>"
    await callback.message.edit_text(text, reply_markup=profile_menu(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=MAIN_MENU_TEXT, reply_markup=main_inline_menu(), parse_mode="HTML")
    await callback.answer()

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    print("Бот-гарант запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
