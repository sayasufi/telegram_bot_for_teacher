from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from source.lexicon.lexicon import LEXICON


def create_schedule_keyboard(*args: str) -> InlineKeyboardMarkup:
    # Создаем объект клавиатуры
    kb_builder = InlineKeyboardBuilder()
    # Добавляем в билдер ряд с кнопками
    kb_builder.row(
        *[
            InlineKeyboardButton(
                text=LEXICON[button] if button in LEXICON else button,
                callback_data=button,
            )
            for button in args
        ],
        width=1
    )
    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()
