import asyncio
import logging
import os
import json
from datetime import date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import OpenAI

# ========== НАСТРОЙКИ ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_BOT_TOKEN or not DEEPSEEK_API_KEY:
    raise Exception("❌ Ошибка: не заданы переменные окружения!")

USER_DATA_FILE = "user_data.json"

logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ========== СИСТЕМА БАЛАНСА ==========
def load_users():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f)

def get_user(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "stars": 0,
            "free_requests": 4,
            "last_reset": str(date.today()),
            "total_requests": 0
        }
        save_users(users)
    return users[user_id_str]

def update_user(user_id, data):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        get_user(user_id)
        users = load_users()
    for key, value in data.items():
        users[user_id_str][key] = value
    save_users(users)

def check_and_reset_free(user_id):
    user = get_user(user_id)
    last_reset = user.get("last_reset", "")
    today = str(date.today())
    
    if last_reset != today:
        update_user(user_id, {
            "free_requests": 4,
            "last_reset": today
        })
        return True
    return False

def use_request(user_id):
    user = get_user(user_id)
    check_and_reset_free(user_id)
    user = get_user(user_id)
    
    if user["stars"] > 0:
        update_user(user_id, {"stars": user["stars"] - 1})
        update_user(user_id, {"total_requests": user["total_requests"] + 1})
        return True, "star", user["stars"] - 1
    elif user["free_requests"] > 0:
        update_user(user_id, {"free_requests": user["free_requests"] - 1})
        update_user(user_id, {"total_requests": user["total_requests"] + 1})
        remaining = user["free_requests"] - 1
        return True, "free", remaining
    return False, "none", 0

def add_stars(user_id, amount):
    user = get_user(user_id)
    update_user(user_id, {"stars": user["stars"] + amount})

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤖 Задать вопрос", callback_data="ask_question"),
        InlineKeyboardButton(text="⭐ Баланс", callback_data="show_balance")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Купить звёзды", callback_data="buy_stars"),
        InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Партнёрам", callback_data="partners"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="help")
    )
    return builder.as_markup()

def buy_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐ 50 звёзд — 50⭐", callback_data="buy_50"),
        InlineKeyboardButton(text="⭐ 100 звёзд — 100⭐", callback_data="buy_100")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ 200 звёзд — 200⭐", callback_data="buy_200"),
        InlineKeyboardButton(text="⭐ 500 звёзд — 500⭐", callback_data="buy_500")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ 1000 звёзд — 1000⭐", callback_data="buy_1000"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    )
    return builder.as_markup()

# ========== ЦЕНЫ ==========
STAR_PACKS = {
    "buy_50": 50,
    "buy_100": 100,
    "buy_200": 200,
    "buy_500": 500,
    "buy_1000": 1000
}

PRICES = {
    "buy_50": 50,
    "buy_100": 100,
    "buy_200": 200,
    "buy_500": 500,
    "buy_1000": 1000
}

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    check_and_reset_free(user_id)
    user = get_user(user_id)
    
    text = f"""
🌟 <b>Добро пожаловать, {name}!</b> 🌟

🤖 <b>AI Assistant Pro</b> — мощный ИИ-помощник

<b>Ваш баланс:</b>
⭐ Звёзд: {user['stars']}
🎁 Бесплатных запросов сегодня: {user['free_requests']}/4

<b>💎 Курс:</b>
1 звезда = 1 запрос к ИИ
4 бесплатных запроса в день

👇 <b>Выберите действие:</b>
"""
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())
    print(f"🆕 {name} (@{message.from_user.username}) ID: {user_id}")

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    text = f"""
📋 <b>Главное меню</b>

⭐ Звёзд: {user['stars']}
🎁 Бесплатно сегодня: {user['free_requests']}/4
"""
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(F.data == "ask_question")
async def ask_question(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    check_and_reset_free(user_id)
    user = get_user(user_id)
    
    if user["stars"] == 0 and user["free_requests"] == 0:
        await callback.message.edit_text(
            "❌ <b>Нет доступных запросов!</b>\n\n"
            "Купите звёзды в меню, чтобы продолжить!",
            parse_mode="HTML",
            reply_markup=buy_menu()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "✍️ <b>Напишите ваш вопрос</b>\n\n"
        "Я отвечу быстро и полезно!\n\n"
        f"💎 <i>Спишется: 1 запрос</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "show_balance")
async def show_balance(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    check_and_reset_free(user_id)
    user = get_user(user_id)
    
    text = f"""
⭐ <b>Ваш баланс</b> ⭐

💰 <b>Звёзд:</b> {user['stars']}
🎁 <b>Бесплатных запросов сегодня:</b> {user['free_requests']}/4
📊 <b>Всего запросов:</b> {user['total_requests']}

💡 1 звезда = 1 запрос к ИИ
"""
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=buy_menu())
    await callback.answer()

@dp.callback_query(F.data == "buy_stars")
async def buy_stars(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⭐ <b>Магазин звёзд</b> ⭐\n\n"
        "1 Telegram Star = 1 внутренняя звезда = 1 запрос\n\n"
        "<b>Доступные пакеты:</b>\n"
        "• 50 звёзд — 50 Telegram Stars\n"
        "• 100 звёзд — 100 Telegram Stars\n"
        "• 200 звёзд — 200 Telegram Stars\n"
        "• 500 звёзд — 500 Telegram Stars\n"
        "• 1000 звёзд — 1000 Telegram Stars\n\n"
        "<i>Оплата через Telegram Stars — мгновенно!</i>",
        parse_mode="HTML",
        reply_markup=buy_menu()
    )
    await callback.answer()

for callback_data, stars_count in STAR_PACKS.items():
    @dp.callback_query(F.data == callback_data)
    async def handle_buy(callback: types.CallbackQuery, stars=stars_count, cb_data=callback_data):
        price = PRICES[cb_data]
        
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"⭐ {stars} звёзд для AI Assistant",
            description=f"{stars} запросов к ИИ. 1:1 курс!",
            payload=f"stars_{stars}",
            provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice(label=f"{stars} звёзд", amount=price)],
            start_parameter="ai_assistant_stars",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💎 Оплатить звёздами Telegram", pay=True)
            ]])
        )
        await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(F.successful_payment)
async def payment_success(message: types.Message):
    stars_count = int(message.successful_payment.payload.split("_")[1])
    user_id = message.from_user.id
    
    add_stars(user_id, stars_count)
    user = get_user(user_id)
    
    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"⭐ Начислено: {stars_count} звёзд\n"
        f"💰 Ваш баланс: {user['stars']} звёзд ({user['stars']} запросов)\n\n"
        f"Теперь вы можете задавать вопросы!",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    
    print(f"💸 Покупка: {message.from_user.first_name} | +{stars_count} звёзд")

@dp.callback_query(F.data == "promo")
async def promo_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎁 <b>Промокоды</b>\n\n"
        "Введите промокод командой:\n"
        "<code>/promo КОД</code>\n\n"
        "<b>Доступные промокоды:</b>\n"
        "• <code>START2024</code> — +5 звёзд\n"
        "• <code>FRIEND2024</code> — +10 звёзд\n"
        "• <code>VIP2025</code> — +25 звёзд\n\n"
        "<i>Следите за новыми промокодами!</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
        ]])
    )
    await callback.answer()

@dp.message(Command("promo"))
async def apply_promo(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /promo <код>")
        return
    
    promo_code = args[1].upper()
    promos = {
        "START2024": 5,
        "FRIEND2024": 10,
        "VIP2025": 25
    }
    
    if promo_code in promos:
        add_stars(message.from_user.id, promos[promo_code])
        user = get_user(message.from_user.id)
        await message.answer(
            f"✅ <b>Промокод активирован!</b>\n"
            f"+{promos[promo_code]} звёзд\n"
            f"💰 Баланс: {user['stars']} звёзд",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Неверный промокод")

@dp.callback_query(F.data == "partners")
async def partners(callback: types.CallbackQuery):
    bot_info = await bot.get_me()
    text = f"""
📢 <b>Партнёрская программа</b>

<b>Ваша реферальная ссылка:</b>
<code>https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}</code>

<b>Условия:</b>
• Друг получает +2 бесплатных запроса
• Вы получаете 20% от его покупок звёзд
"""
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    ]]))
    await callback.answer()

@dp.callback_query(F.data == "help")
async def help_menu(callback: types.CallbackQuery):
    text = """
❓ <b>Помощь</b>

<b>Команды:</b>
/start — Главное меню
/promo КОД — Активировать промокод

<b>Тарифы:</b>
• 4 бесплатных запроса в день
• 1 звезда = 1 запрос
• Покупка звёзд — в магазине

<b>Курс обмена:</b>
1 Telegram Star = 1 внутренняя звезда = 1 запрос к ИИ
"""
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    ]]))
    await callback.answer()

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_question(message: types.Message):
    user_id = message.from_user.id
    check_and_reset_free(user_id)
    
    success, payment_type, remaining = use_request(user_id)
    
    if not success:
        await message.answer(
            "❌ <b>Нет доступных запросов!</b>\n\n"
            "Купите звёзды в меню!",
            parse_mode="HTML",
            reply_markup=buy_menu()
        )
        return
    
    thinking = await message.answer("🤔 <i>Думаю...</i>", parse_mode="HTML")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты — профессиональный AI-ассистент. Отвечай полезно и дружелюбно."},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        
        if payment_type == "star":
            answer += f"\n\n---\n💫 <i>Списано: 1 звезда. Осталось: {remaining} звёзд</i>"
        elif payment_type == "free":
            answer += f"\n\n---\n🎁 <i>Бесплатный запрос. Осталось сегодня: {remaining}/4</i>"
        
        await thinking.edit_text(answer, parse_mode="HTML")
        
    except Exception as e:
        await thinking.edit_text(f"❌ <b>Ошибка:</b> {e}", parse_mode="HTML")

async def main():
    print("🚀 Бот запущен! 1 Telegram Star = 1 запрос")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
