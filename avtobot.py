import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

TOKEN = "8789091547:AAEjkkIM5fMvUN3uF2hVbOjYL8RVeJB7TQA"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = {}

ADMIN_ID = 8964200951
ADMIN_USERNAME = "@verrtony"
subscriptions_db = {}

class OfferStates(StatesGroup):
    waiting_link = State()
    waiting_price = State()
    waiting_currency = State()

START_TEXT = """Привет! 👋 Я бот для создания офферов на подарки.

Выбери действие ниже:"""

HELP_TEXT = """🛠 <b>Как создать оффер:</b>

1️⃣ Убедись, что у тебя есть активная подписка (напиши /check).
2️⃣ Нажми кнопку «Создать оффер» и следуй инструкциям.

⚙️ <b>Доступные валюты:</b>
<code>stars</code> — звезды ⭐️
<code>gra</code> — граммы 💎"""

def is_subscribed(user_id: int) -> bool:
    if user_id not in subscriptions_db:
        return False
    return subscriptions_db[user_id] > datetime.now()

def kb_start():
    b = InlineKeyboardBuilder()
    b.button(text="📖 Как пользоваться", callback_data="help")
    b.button(text="🚀 Создать оффер", callback_data="create_offer")
    b.button(text="💎 Купить подписку", callback_data="buy_sub")
    b.adjust(1)
    return b.as_markup()

def kb_cancel():
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="cancel_offer")
    return b.as_markup()

def kb_currency():
    b = InlineKeyboardBuilder()
    b.button(text="⭐️ Stars", callback_data="cur_stars")
    b.button(text="💎 Gram", callback_data="cur_gra")
    b.button(text="❌ Отмена", callback_data="cancel_offer")
    b.adjust(2, 1)
    return b.as_markup()

def kb_offer(link, price, cur):
    b = InlineKeyboardBuilder()
    b.button(text="Отклонить", callback_data="no")
    b.button(text="Принять", callback_data=f"yes_{link}_{price}_{cur}")
    b.adjust(2)
    return b.as_markup()

def kb_transfer(link, uname):
    b = InlineKeyboardBuilder()
    b.button(text=f"Передать NFT @{uname}", url=f"https://t.me/{uname}")
    b.button(text="Как передать", callback_data=f"how_{link}")
    b.adjust(1)
    return b.as_markup()

def fmt(p, c):
    return f"{p} ⭐️" if c == "stars" else f"{p} 💎"

@dp.callback_query(lambda c: c.data == 'create_offer')
async def start_create(c: types.CallbackQuery, state: FSMContext):
    if not is_subscribed(c.from_user.id):
        return await c.answer("❌ У вас нет активной подписки.", show_alert=True)
    
    await c.message.edit_text("Шаг 1/3. Отправьте ссылку на подарок (например: https://t.me/nft/PlushPepe-123):", reply_markup=kb_cancel())
    await state.set_state(OfferStates.waiting_link)
    await c.answer()

@dp.message(OfferStates.waiting_link)
async def process_link(m: types.Message, state: FSMContext):
    if "t.me/nft/" not in m.text:
        return await m.answer("❌ Это не похоже на ссылку на подарок. Попробуй еще раз:")
    
    await state.update_data(link=m.text)
    await m.answer("Шаг 2/3. Введите цену (только цифры):", reply_markup=kb_cancel())
    await state.set_state(OfferStates.waiting_price)

@dp.message(OfferStates.waiting_price)
async def process_price(m: types.Message, state: FSMContext):
    if not m.text.isdigit():
        return await m.answer("❌ Цена должна быть числом. Введите еще раз:")
    
    await state.update_data(price=m.text)
    await m.answer("Шаг 3/3. Выберите валюту:", reply_markup=kb_currency())
    await state.set_state(OfferStates.waiting_currency)

@dp.callback_query(lambda c: c.data.startswith('cur_'))
async def process_currency(c: types.CallbackQuery, state: FSMContext):
    cur = "stars" if c.data == "cur_stars" else "gra"
    data = await state.get_data()
    link = data['link']
    price = data['price']
    uname = c.from_user.username or c.from_user.first_name
    
    db[link.split("/")[-1]] = (price, cur, uname)
    await state.clear()
    
    text = f"✅ Оффер готов!\n\nТеперь отправьте в любой чат:\n`/offer {link}`"
    await c.message.edit_text(text, parse_mode="Markdown")
    await c.answer()

@dp.callback_query(lambda c: c.data == 'cancel_offer')
async def cancel_create(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(START_TEXT, reply_markup=kb_start(), parse_mode="HTML")
    await c.answer()

async def do_offer(m: types.Message):
    if not is_subscribed(m.from_user.id):
        return await m.answer("❌ У вас нет активной подписки.")
        
    a = m.text.split()
    if len(a) < 2: return await m.answer("Формат: /offer ссылка")
    link = a[1]
    gid = link.split("/")[-1]
    
    if gid not in db: return await m.answer("Сначала создай оффер через кнопку «Создать оффер»")
    p, c, uname = db[gid]
    
    text = f"Пользователь {uname} предлагает Вам {fmt(p, c)} за подарок <a href='{link}'>{gid.replace('-', ' #')}</a>"
    
    try:
        await m.edit_text(text, reply_markup=kb_offer(link, p, c), parse_mode="HTML", disable_web_page_preview=False)
    except Exception:
        await m.answer(text, reply_markup=kb_offer(link, p, c), parse_mode="HTML", disable_web_page_preview=False)

@dp.message(Command("start"))
async def st(m: types.Message): await m.answer(START_TEXT, reply_markup=kb_start(), parse_mode="HTML")

@dp.business_message(Command("start"))
async def b_st(m: types.Message): await m.answer(START_TEXT, reply_markup=kb_start(), parse_mode="HTML")

@dp.callback_query(lambda c: c.data == 'help')
async def cb_help(c: types.CallbackQuery):
    try: await c.message.edit_text(HELP_TEXT, reply_markup=kb_start(), parse_mode="HTML")
    except TelegramBadRequest: pass
    await c.answer()

@dp.callback_query(lambda c: c.data == 'buy_sub')
async def cb_buy(c: types.CallbackQuery):
    try: await c.message.edit_text(f"💎 Для покупки подписки напишите администратору: {ADMIN_USERNAME}", reply_markup=kb_start(), parse_mode="HTML")
    except TelegramBadRequest: pass
    await c.answer()

@dp.message(Command("offer"))
async def off(m: types.Message): await do_offer(m)

@dp.business_message(Command("offer"))
async def b_off(m: types.Message): await do_offer(m)

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    if is_subscribed(message.from_user.id):
        expire_date = subscriptions_db[message.from_user.id].strftime("%d.%m.%Y %H:%M")
        await message.answer(f"✅ У вас есть активная подписка. Доступно до: {expire_date}")
    else:
        await message.answer("❌ У вас нет активной подписки.")

@dp.message(Command("sub"))
async def cmd_sub(message: types.Message):
    if message.from_user.id != ADMIN_ID: return await message.answer("У вас нет прав.")
    args = message.text.split()
    if len(args) < 3: return await message.answer("Формат: /sub user_id days")
    try:
        target_user_id = int(args[1])
        days = int(args[2])
    except ValueError: return await message.answer("ID и дни должны быть числами.")
    subscriptions_db[target_user_id] = datetime.now() + timedelta(days=days)
    await message.answer(f"🎉 Подписка для {target_user_id} выдана на {days} дней.")
    try: await bot.send_message(target_user_id, f"🎁 Вам выдана подписка на {days} дней!")
    except Exception: pass

@dp.callback_query(lambda c: c.data.startswith('yes_'))
async def acc(c: types.CallbackQuery):
    _, link, price, cur = c.data.split("_")
    gift = link.split("/")[-1].replace('-', ' #')
    gid = link.split("/")[-1]
    uname = db.get(gid, (0, 0, "username"))[2]
    
    text = f"🎁 Подарок: <a href='{link}'>{gift}</a> успешно продан!\n\n🎁 Передайте подарок покупателю для зачисления {fmt(price, cur)}."
    
    try: await c.message.edit_text(text, reply_markup=kb_transfer(link, uname), parse_mode="HTML", disable_web_page_preview=False)
    except TelegramBadRequest: pass
    await c.answer()

@dp.callback_query(lambda c: c.data.startswith('how_'))
async def how(c: types.CallbackQuery):
    link = c.data.replace("how_", "")
    gid = link.split("/")[-1]
    uname = db.get(gid, (0, 0, "username"))[2]
    gift = gid.replace('-', ' #')
    
    b = InlineKeyboardBuilder()
    b.button(text="Вернуться к передаче", callback_data=f"back_{link}")
    b.adjust(1)
    text = f"Как передать подарок пользователю: @{uname}\n\n1. Передайте подарок пользователю: @{uname}.\n2. Нажмите «Передать NFT» и выберите {gift}.\n3. Подтвердите передачу подарка.\n\nTelegram зафиксирует транзакцию."
    try: await c.message.edit_text(text, reply_markup=b.as_markup())
    except TelegramBadRequest: pass
    await c.answer()

@dp.callback_query(lambda c: c.data.startswith('back_'))
async def back(c: types.CallbackQuery):
    link = c.data.replace("back_", "")
    gift = link.split("/")[-1].replace('-', ' #')
    gid = link.split("/")[-1]
    price, cur, uname = db.get(gid, ("0", "stars", "username"))
    
    text = f"🎁 Подарок: <a href='{link}'>{gift}</a> успешно продан!\n\n🎁 Передайте подарок покупателю для зачисления {fmt(price, cur)}."
    
    try: await c.message.edit_text(text, reply_markup=kb_transfer(link, uname), parse_mode="HTML", disable_web_page_preview=False)
    except TelegramBadRequest: pass
    await c.answer()

@dp.callback_query(lambda c: c.data == 'no')
async def dec(c: types.CallbackQuery):
    try: await c.message.edit_text("❌ Оффер отклонен.")
    except TelegramBadRequest: pass
    await c.answer()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())