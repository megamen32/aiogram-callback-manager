import asyncio
import os
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup

from aiogram_callback_manager import AsyncCallbackManager

API_TOKEN = os.environ["API_TOKEN"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
callback_manager = AsyncCallbackManager(use_json=False)
dp.include_router(callback_manager.router)


class Product:
    def __init__(self, name: str, price: int):
        self.name = name
        self.price = price

    def __str__(self):
        return self.name


products = [
    Product(name=f"Product {i}", price=random.randint(100, 1_000_000))
    for i in range(1, 101)
]


@callback_manager.callback_handler()
async def product_list(callback_query: types.CallbackQuery, page: int = 1):
    keyboard_rows = await callback_manager.create_buttons(
        objects=products,
        display_func=product_list,
        button_func=product_detail,
        user_data=callback_query,
        page=page,
        objects_per_page=10,
    )

    await callback_query.message.edit_text(
        text=f"Products · page {page}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows),
    )


@callback_manager.callback_handler()
async def product_detail(callback_query: types.CallbackQuery, element: Product):
    await callback_query.answer(
        f"You selected {element.name} for {element.price}",
        show_alert=True,
    )


@dp.message(Command("start"))
async def start_command(message: types.Message):
    button = await callback_manager.create_button(
        text="Products",
        func=product_list,
        user_data=message,
    )

    await message.answer(
        "Menu",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[button]]),
    )


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
