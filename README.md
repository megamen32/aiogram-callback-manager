# aiogram-callback-manager

Build rich aiogram inline menus without fighting Telegram's `callback_data` limit.

`aiogram-callback-manager` lets you attach Python handlers and arguments to inline buttons, store the real payload in a backend, and send Telegram only a short callback key. It is useful for bots with dynamic menus, paginated lists, nested screens, back buttons, and object-based actions where raw `callback_data` strings quickly become fragile.

Instead of manually encoding IDs, states, page numbers, filters, and action names into a 64-byte callback string, you create a button for a handler and pass normal Python arguments. The manager saves the payload, restores it on click, and calls the right async function.

## Why use it?

- **Cleaner aiogram handlers** — write callback handlers as normal async Python functions.
- **No manual callback encoding** — stop packing and parsing complex `callback_data` strings by hand.
- **Large callback payloads** — store payloads in SQLite or your own storage and send only a short hash to Telegram.
- **Dynamic inline keyboards** — generate buttons from Python objects and pass the selected object to the handler.
- **Pagination built in** — create paginated menus with page buttons and a `noop` current-page button.
- **Back-button flow** — pass a previous callback as `back_btn` and return to the previous menu.
- **Pluggable storage** — use the built-in SQLite storage or implement the storage interface for another backend.
- **JSON or pickle serialization** — choose safer JSON-compatible payloads or more flexible Python object serialization.

## Minimal example

```python
import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup

from aiogram_callback_manager import AsyncCallbackManager

bot = Bot(token=os.environ["API_TOKEN"])
dp = Dispatcher()

callback_manager = AsyncCallbackManager(use_json=False)
dp.include_router(callback_manager.router)


@callback_manager.callback_handler()
async def show_message(callback_query: types.CallbackQuery, message_text: str):
    await callback_query.message.edit_text(f"You selected: {message_text}")


@dp.message(Command("start"))
async def start(message: types.Message):
    button = await callback_manager.create_button(
        text="Click me",
        func=show_message,
        user_data=message,
        message_text="Hello from callback storage!",
    )

    await message.answer(
        "Choose an option:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[button]]),
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

When the user clicks the button, the manager loads the stored payload and calls:

```python
await show_message(callback_query, message_text="Hello from callback storage!")
```

## Paginated object list

`create_buttons()` builds a keyboard from a list of objects. The selected item is passed to the target handler as `element`.

```python
import random

from aiogram import types
from aiogram.types import InlineKeyboardMarkup


class Product:
    def __init__(self, name: str, price: int):
        self.name = name
        self.price = price

    def __str__(self):
        return self.name


products = [
    Product(name=f"Product {i}", price=random.randint(100, 10_000))
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
        f"{element.name}: {element.price}",
        show_alert=True,
    )
```

## Nested menus and back buttons

A callback can receive a generated `back_btn` if the handler has a `back_btn` parameter. This makes nested menus easier to implement without manually rebuilding previous callback payloads.

```python
from typing import Optional

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@callback_manager.callback_handler()
async def category_list(callback_query: types.CallbackQuery):
    button = await callback_manager.create_button(
        text="Books",
        func=item_list,
        user_data=callback_query,
        category="books",
        back_btn=callback_query,
    )

    await callback_query.message.edit_text(
        "Categories",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[button]]),
    )


@callback_manager.callback_handler()
async def item_list(
    callback_query: types.CallbackQuery,
    category: str,
    back_btn: Optional[InlineKeyboardButton] = None,
):
    rows = [
        [
            await callback_manager.create_button(
                text="Open item",
                func=item_detail,
                user_data=callback_query,
                category=category,
                item_id=1,
                back_btn=callback_query,
            )
        ]
    ]

    if back_btn is not None:
        rows.append([back_btn])

    await callback_query.message.edit_text(
        f"Items in {category}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@callback_manager.callback_handler()
async def item_detail(
    callback_query: types.CallbackQuery,
    category: str,
    item_id: int,
    back_btn: Optional[InlineKeyboardButton] = None,
):
    rows = [[back_btn]] if back_btn is not None else []

    await callback_query.message.edit_text(
        f"Item #{item_id} from {category}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
```

## Installation

```bash
pip install aiogram-callback-manager
```

Requirements:

- Python 3.10+
- aiogram 3.x
- aiosqlite

For local development:

```bash
git clone https://github.com/megamen932/aiogram-callback-manager.git
cd aiogram-callback-manager
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Basic setup

```python
from aiogram import Bot, Dispatcher
from aiogram_callback_manager import AsyncCallbackManager

bot = Bot(token="YOUR_TELEGRAM_BOT_TOKEN")
dp = Dispatcher()

callback_manager = AsyncCallbackManager(use_json=False)
dp.include_router(callback_manager.router)
```

The manager initializes its storage during construction. You can also call `await callback_manager.init_db()` explicitly if your application lifecycle requires it.

## Serialization modes

### Pickle mode

```python
callback_manager = AsyncCallbackManager(use_json=False)
```

Pickle mode is the most flexible option. It can store many Python objects, including custom classes. Use it when your bot controls the stored payload and you trust the local storage.

### JSON mode

```python
callback_manager = AsyncCallbackManager(use_json=True)
```

JSON mode stores JSON-compatible values. Dataclasses are converted with `asdict()`. Use this mode when you prefer portable, inspectable payloads.

## Custom storage

The built-in storage is SQLite-based. To use another backend, implement `CallbackDataStorage` and pass it to the manager.

```python
from aiogram_callback_manager.base_db_storage import CallbackDataStorage


class RedisCallbackStorage(CallbackDataStorage):
    async def save(self, data_hash: str, data_bytes: bytes, timestamp: float, user_id: int):
        ...

    async def load(self, data_hash: str, user_id: int):
        ...

    async def clean_old(self, expiry_time: int):
        ...

    async def init_db(self):
        ...


callback_manager = AsyncCallbackManager(storage=RedisCallbackStorage())
```

## Cleaning old callback data

Old callback payloads can be removed manually:

```python
await callback_manager.clean_old_callback_data(expiry_time=3600)
```

Or automatically:

```python
callback_manager = AsyncCallbackManager(
    auto_clean=True,
    expiry_time=3600,
    pause_between_cleaning=3600,
)
```

## API overview

### `callback_handler(*filters)`

Registers a coroutine as a managed callback handler.

```python
@callback_manager.callback_handler()
async def handler(callback_query: types.CallbackQuery, value: int):
    ...
```

### `create_button(text, func, user_data, back_btn=None, *args, **kwargs)`

Creates an `InlineKeyboardButton` and stores the handler payload.

- `text` — button label.
- `func` — handler function or handler name.
- `user_data` — a Telegram user source: `user_id`, `Message`, or `CallbackQuery`.
- `back_btn` — optional previous callback/button data for navigation.
- `*args`, `**kwargs` — values passed to the handler on click.

### `create_buttons(objects, display_func, button_func, user_data, ...)`

Creates rows of inline buttons from a list of objects and appends pagination controls.

The selected object is passed to `button_func` as `element`.

### `create_paginate_buttons(func, total_pages, current_page, user_data, ...)`

Creates page navigation buttons for a manually built list.

## Security notes

- Callback payloads are scoped by `user_id`, so another user cannot reuse a stored callback hash successfully.
- Pickle is powerful but should only be used with trusted local data. If you need portable or inspectable payloads, prefer JSON mode.
- Old callback data should be cleaned periodically for long-running bots.

## Examples

See the `examples/` directory:

- `basic_example.py` — a simple menu and product list.
- `example_auto_list.py` — object-based list generation.
- `example_menu_and_back_button.py` — nested menus with back navigation.

## License

This project is distributed under the license included in the repository.
