import datetime

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from source.database.database import week_days
from source.keyboards.other_keyboard import create_schedule_keyboard
from .user_handlers import client

router = Router()

storage = MemoryStorage()

collection = client["user_bd"]["user"]


class Money(StatesGroup):
    days = State()
    student = State()
    count = State()


@router.message(Command(commands="earnings"))
async def process_earnings(message: Message, state: FSMContext):
    await message.answer(
        text="За какой день вы хотите внести доход?",
        reply_markup=create_schedule_keyboard(
            "today", 'yesterday', "another date", "cancel"
        ),
    )
    await state.set_state(Money.days)


@router.callback_query(F.data == "today", StateFilter(Money.days))
async def process_earnings_today(callback: CallbackQuery, state: FSMContext):
    year = callback.message.date.year
    month = callback.message.date.month
    hour = callback.message.date.hour + collection.find_one({"id": callback.from_user.id})['time_zone']

    if hour > 24:
        day = callback.message.date.day + 1
    else:
        day = callback.message.date.day
    await state.update_data(days=f'{day}.{month}.{year}')

    weekday = datetime.datetime(day=day, month=month, year=year).weekday()

    await callback.message.answer(
        text=f"Выберите ученика, за которого вам сегодня заплатили.",
        reply_markup=create_schedule_keyboard(
            *collection.find_one({"id": callback.from_user.id})['data']['schedule'][week_days[weekday]].keys(), 'cancel'
        ),
    )
    await state.set_state(Money.student)


@router.callback_query(F.data == "yesterday", StateFilter(Money.days))
async def process_earnings_yesterday(callback: CallbackQuery, state: FSMContext):
    year = callback.message.date.year
    month = callback.message.date.month
    hour = callback.message.date.hour + collection.find_one({"id": callback.from_user.id})['time_zone']
    if hour > 24:
        day = callback.message.date.day
    else:
        day = callback.message.date.day - 1
    await state.update_data(days=f'{day}.{month}.{year}')

    weekday = datetime.datetime(day=day, month=month, year=year).weekday()

    await callback.message.answer(
        text=f"Выберите ученика, за которого вам сегодня заплатили.",
        reply_markup=create_schedule_keyboard(
            *collection.find_one({"id": callback.from_user.id})['data']['schedule'][week_days[weekday]].keys(), 'cancel'
        ),
    )
    await state.set_state(Money.student)


@router.callback_query(StateFilter(Money.student))
async def process_earnings_yesterday(callback: CallbackQuery, state: FSMContext):
    year = callback.message.date.year
    month = callback.message.date.month
    hour = callback.message.date.hour + collection.find_one({"id": callback.from_user.id})['time_zone']
    if hour > 24:
        day = callback.message.date.day
    else:
        day = callback.message.date.day - 1
    await state.update_data(days=f'{day}.{month}.{year}')
    await state.set_state(Money.student)
