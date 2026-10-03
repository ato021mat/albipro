"""
AlbiPro Telegram Bot - Version 1.0 (Simplified for monetization)
این فایل را کامل کپی کنید. بعداً ویژگی‌های بیشتری اضافه می‌کنیم.
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    SuccessfulPayment,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ==================== تنظیمات ====================
# توکن بات را از BotFather بگیرید و اینجا بگذارید یا به عنوان متغیر محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN", "8990421292:AAH_Yt8mi3P7mtn9kIe5pP1TAGWf-sxrWPc")

# آیدی تلگرام خودت (دو تا برای unlimited). از @userinfobot بگیر
ADMIN_IDS = [75054572, 5487258653]  # این اعداد را عوض کن

# تعداد توکن رایگان اولیه
FREE_TOKENS = 50

# قیمت‌ها (Stars)
# 50 Stars = 100 توکن
PACKAGES = {
    "pack_100": {"tokens": 100, "stars": 50, "label": "۱۰۰ توکن"},
    "pack_300": {"tokens": 300, "stars": 120, "label": "۳۰۰ توکن (۲۰٪ تخفیف)"},
    "pack_1000": {"tokens": 1000, "stars": 350, "label": "۱۰۰۰ توکن (۳۰٪ تخفیف)"},
}

# هزینه هر عملیات (توکن)
COST_PRICE_CHECK = 2
COST_SIMPLE_CRAFT = 5

# حداکثر کاربران فعال اولیه (برای روان بودن روی هاست رایگان)
MAX_USERS = 100

# ==================== دیتابیس ====================
DB_PATH = "albi_users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            tokens INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT,
            last_active TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount_tokens INTEGER,
            stars_paid INTEGER,
            payload TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_user(user_id: int, username: str | None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # چک تعداد کاربران
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    if count >= MAX_USERS and user_id not in ADMIN_IDS:
        conn.close()
        return False  # ظرفیت پر

    is_admin = 1 if user_id in ADMIN_IDS else 0
    tokens = 999999 if is_admin else FREE_TOKENS
    now = datetime.utcnow().isoformat()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, tokens, is_admin, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, tokens, is_admin, now, now)
    )
    conn.commit()
    conn.close()
    return True

def update_tokens(user_id: int, delta: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET tokens = tokens + ?, last_active = ? WHERE user_id = ?",
              (delta, datetime.utcnow().isoformat(), user_id))
    conn.commit()
    conn.close()

def get_tokens(user_id: int) -> int:
    user = get_user(user_id)
    if user:
        return user[2]  # tokens column
    return 0

def set_admin(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 1, tokens = 999999 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ==================== بات ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if not get_user(user_id):
        success = create_user(user_id, username)
        if not success:
            await message.answer(
                "⚠️ متأسفانه ظرفیت کاربران فعلی پر شده است.\n"
                "لطفاً بعداً دوباره تلاش کنید یا به ادمین پیام دهید."
            )
            return
        await message.answer(
            f"👋 سلام! به <b>AlbiPro Bot</b> خوش آمدید.\n\n"
            f"شما <b>{FREE_TOKENS} توکن رایگان</b> دریافت کردید.\n\n"
            f"از منوی زیر استفاده کنید:"
        )
    else:
        await message.answer("دوباره خوش آمدید! از منوی زیر استفاده کنید.")

    await show_main_menu(message)

async def show_main_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 موجودی من", callback_data="balance")],
        [InlineKeyboardButton(text="🛒 خرید توکن (Stars)", callback_data="buy")],
        [InlineKeyboardButton(text="📊 چک قیمت ساده", callback_data="price_help")],
        [InlineKeyboardButton(text="ℹ️ راهنما", callback_data="help")],
    ])
    await message.answer("منوی اصلی:", reply_markup=kb)

@dp.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    tokens = get_tokens(callback.from_user.id)
    user = get_user(callback.from_user.id)
    is_admin = user and user[3] == 1
    text = f"💰 موجودی شما: <b>{tokens}</b> توکن"
    if is_admin:
        text += "\n\n👑 شما ادمین هستید (نامحدود)"
    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "buy")
async def cb_buy(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['label']} - {p['stars']} Stars", callback_data=f"buy_{k}")]
        for k, p in PACKAGES.items()
    ])
    await callback.message.answer(
        "پکیج مورد نظر را انتخاب کنید:\n"
        "(پرداخت با Telegram Stars انجام می‌شود)",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy_pack(callback: CallbackQuery):
    pack_id = callback.data.replace("buy_", "")
    if pack_id not in PACKAGES:
        await callback.answer("پکیج نامعتبر", show_alert=True)
        return
    pack = PACKAGES[pack_id]
    prices = [LabeledPrice(label=pack["label"], amount=pack["stars"])]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"خرید {pack['label']}",
        description=f"{pack['tokens']} توکن برای استفاده در AlbiPro Bot",
        payload=f"{pack_id}_{callback.from_user.id}",
        provider_token="",  # برای Stars خالی
        currency="XTR",
        prices=prices,
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment: SuccessfulPayment = message.successful_payment
    payload = payment.invoice_payload
    # payload = pack_id_userid
    parts = payload.split("_")
    if len(parts) < 2:
        return
    pack_id = parts[0]
    if pack_id not in PACKAGES:
        return
    pack = PACKAGES[pack_id]
    user_id = message.from_user.id
    update_tokens(user_id, pack["tokens"])

    # ذخیره تراکنش
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (user_id, amount_tokens, stars_paid, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, pack["tokens"], payment.total_amount, payload, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ پرداخت موفق!\n"
        f"{pack['tokens']} توکن به حساب شما اضافه شد.\n"
        f"موجودی جدید: {get_tokens(user_id)} توکن"
    )

@dp.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    text = (
        "<b>راهنمای AlbiPro Bot</b>\n\n"
        "این بات نسخه ساده‌شده ابزارهای Albion Online است.\n"
        "هر عملیات مقداری توکن مصرف می‌کند.\n\n"
        f"• چک قیمت ساده: {COST_PRICE_CHECK} توکن\n"
        f"• محاسبه کرافت ساده: {COST_SIMPLE_CRAFT} توکن\n\n"
        "توکن رایگان اولیه دارید. برای ادامه شارژ کنید.\n"
        "پرداخت فقط با Telegram Stars یا بعداً کریپتو.\n\n"
        "ویژگی‌های کامل‌تر به مرور اضافه می‌شود."
    )
    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "price_help")
async def cb_price_help(callback: CallbackQuery):
    await callback.message.answer(
        "برای چک قیمت، دستور زیر را بفرستید:\n\n"
        "<code>/price ITEM_ID</code>\n\n"
        "مثال:\n"
        "<code>/price T4_BAG</code>\n\n"
        f"هزینه: {COST_PRICE_CHECK} توکن"
    )
    await callback.answer()

@dp.message(Command("price"))
async def cmd_price(message: Message):
    user_id = message.from_user.id
    tokens = get_tokens(user_id)
    if tokens < COST_PRICE_CHECK and user_id not in ADMIN_IDS:
        await message.answer(f"❌ توکن کافی ندارید. موجودی: {tokens}")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("مثال: /price T4_BAG")
        return

    item_id = args[1].strip().upper()
    # اینجا بعداً API واقعی را وصل می‌کنیم. فعلاً دمو
    await message.answer(
        f"🔍 در حال جستجوی قیمت <b>{item_id}</b>...\n"
        f"(این نسخه دمو است. در نسخه بعدی قیمت واقعی از albion-online-data می‌آید)"
    )
    # کم کردن توکن
    if user_id not in ADMIN_IDS:
        update_tokens(user_id, -COST_PRICE_CHECK)
    await message.answer(f"✅ {COST_PRICE_CHECK} توکن کسر شد. موجودی: {get_tokens(user_id)}")

# دستور ادمین برای ست کردن unlimited
@dp.message(Command("setadmin"))
async def cmd_setadmin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("مثال: /setadmin 123456789")
        return
    try:
        target = int(args[1])
        set_admin(target)
        await message.answer(f"✅ کاربر {target} ادمین نامحدود شد.")
    except:
        await message.answer("آیدی نامعتبر")

async def main():
    init_db()
    # اطمینان از ادمین‌ها
    for aid in ADMIN_IDS:
        if not get_user(aid):
            create_user(aid, "admin")
        else:
            set_admin(aid)
    print("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
