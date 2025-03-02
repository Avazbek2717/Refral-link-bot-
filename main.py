import sqlite3
import asyncio
import secrets
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# ✅ .env fayldan ma'lumotlarni yuklash
load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SECRET_CHANNEL_BASE_LINK = os.getenv("SECRET_CHANNEL_BASE_LINK")
JOIN_CHANNEL = os.getenv("JOIN_CHANNEL")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ✅ SQLite bazasini yaratish yoki ulanish
conn = sqlite3.connect("referral_bot.db")
cursor = conn.cursor()

# ✅ Jadvalni yaratish
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        phone TEXT,
        referer_id INTEGER,
        referral_count INTEGER DEFAULT 0,
        verified_referrals INTEGER DEFAULT 0,
        referral_link TEXT,
        secret_token TEXT UNIQUE,
        status TEXT DEFAULT 'pending'
    )
''')
conn.commit()

# ✅ Foydalanuvchi kanalga a'zo ekanligini tekshirish
async def is_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ✅ Start komandasi
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    referer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        bot_info = await bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
        cursor.execute("INSERT INTO users (user_id, referer_id, referral_link) VALUES (?, ?, ?)", (user_id, referer_id, referral_link))
        conn.commit()
        if referer_id:
            cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referer_id,))
            conn.commit()
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("📌 Iltimos, telefon raqamingizni yuboring:", reply_markup=keyboard)

# ✅ Foydalanuvchining telefon raqamini qabul qilish
@dp.message(F.contact)
async def get_contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    cursor.execute("UPDATE users SET phone = ?, status = 'active' WHERE user_id = ?", (phone, user_id))
    conn.commit()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga qo‘shilish", url=JOIN_CHANNEL)],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")]
    ])
    await message.answer("📌 Avval kanalga obuna bo‘ling va 'Obunani tekshirish' tugmasini bosing:", reply_markup=keyboard)

# ✅ Obunani tekshirish tugmasi
@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await is_member(user_id):
        cursor.execute("SELECT referer_id, verified_referrals FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        referer_id = user_data[0]

        if referer_id:
            cursor.execute("UPDATE users SET verified_referrals = verified_referrals + 1 WHERE user_id = ?", (referer_id,))
            conn.commit()

            cursor.execute("SELECT verified_referrals FROM users WHERE user_id = ?", (referer_id,))
            verified_referrals = cursor.fetchone()[0]
            if verified_referrals >= 3:
                secret_token = secrets.token_urlsafe(8)
                secret_link = f"{SECRET_CHANNEL_BASE_LINK}?start={secret_token}"
                cursor.execute("UPDATE users SET secret_token = ? WHERE user_id = ?", (secret_token, referer_id))
                conn.commit()
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔐 Maxfiy kanalga kirish", url=secret_link)]
                ])
                
                await bot.send_message(referer_id, "🎉 Siz 5 ta do‘stingizni taklif qildingiz!", reply_markup=keyboard)
        
        cursor.execute("SELECT referral_link FROM users WHERE user_id = ?", (user_id,))
        await callback.message.answer(f"🎉 Siz kanalga muvaffaqiyatli qo‘shildingiz!\n🔗 Referal linkingiz: {cursor.fetchone()[0]}")
        await callback.answer()
    else:
        await callback.answer("❌ Siz hali kanalga a'zo bo‘lmadingiz!", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        conn.close()

# TOKEN = "7772712876:AAHxf8uiRYTNenc4CSfumxmQbL9efsqd1U8"
# CHANNEL_ID = -1002392086684  # Kanal ID sini shu yerga qo'ying
#avazbektoshtonov077
#avazbek2717