from copy import deepcopy
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from source.bot import client
from source.database.database import schedule, price_per_lesson
from source.keyboards.other_keyboard import create_schedule_keyboard
from source.lexicon.lexicon import LEXICON

router = Router()

storage = MemoryStorage()


class Student(StatesGroup):
    day = State()
    text = State()


class Price(StatesGroup):
    money = State()


class Time(StatesGroup):
    time = State()


temp_dict = {}

collection = client["user_bd"]["user"]


# Этот хэндлер будет срабатывать на команду "/start" -
# добавлять пользователя в базу данных, если его там еще не было
# и отправлять ему приветственное сообщение
@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    await message.answer(LEXICON[message.text])
    if not collection.find_one({"id": message.from_user.id}):
        collection.insert_one(
            {
                "id": message.from_user.id,
                "data": {
                    "schedule": deepcopy(schedule),
                    "price_per_lesson": deepcopy(price_per_lesson),
                },
            }
        )
        await message.answer(
            'Напишите сколько сейчас ЧАСОВ по вашему местному времени:\nесли время 21:12, то необходимо вписать 21\nесли время 01:23, то необходимо вписать 1')
        await state.set_state(Time.time)


@router.message(StateFilter(Time.time))
async def process_time_zone_input(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    temp_dict = await state.get_data()
    h = int(temp_dict['time'])
    time_zone = h - message.date.hour
    if time_zone < 0:
        time_zone = 24 + time_zone

    collection.update_one(
        {"id": message.from_user.id},
        {"$set": {'time_zone': time_zone}},
    )
    await message.answer('Ваш часовой пояс успешно сохранен!')
    await message.answer(LEXICON['/help'])
    await state.clear()


# Этот хэндлер будет срабатывать на команду "/help"
# и отправлять пользователю сообщение со списком доступных команд в боте
@router.message(Command(commands="help"))
async def process_help_command(message: Message, state: FSMContext):
    await message.answer(LEXICON[message.text])
    await state.clear()


@router.callback_query(F.data == "cancel")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text=LEXICON["/help"])
    await state.clear()


@router.message(Command(commands="prices"))
async def process_prices(message: Message, state: FSMContext):
    await message.answer(
        text="Вы хотите изменить или посмотреть цены за занятия?",
        reply_markup=create_schedule_keyboard(
            "change prices", "see the prices"
        ),
    )
    await state.clear()


@router.callback_query(F.data == "see the prices")
async def process_see_prices(callback: CallbackQuery, state: FSMContext):
    a = collection.find_one({"id": callback.from_user.id})["data"][
        "price_per_lesson"
    ]
    text = ""
    for key, value in a.items():
        text = f"{text}{key} - {value}руб.\n"
    text = f"<b>Цены за занятия:\n{text}</b>"
    await callback.message.edit_text(
        text=text,
        reply_markup=create_schedule_keyboard("change prices", "cancel"),
    )
    await state.clear()


@router.callback_query(F.data == "change prices")
async def process_change_prices(callback: CallbackQuery, state: FSMContext):
    a = collection.find_one({"id": callback.from_user.id})["data"][
        "price_per_lesson"
    ]
    text = ""
    for key in a:
        text = f"{text}{key} - {a[key]}\n"
    await callback.message.answer(text="<b>Старые цены за занятия:</b>")
    text = f"{text}"
    await callback.message.answer(text=text)
    await callback.message.answer(text="Введите новые цены:")
    await state.set_state(Price.money)


@router.message(StateFilter(Price.money))
async def process_save_money(message: Message, state: FSMContext):
    await state.update_data(money=message.text)
    f = {}
    temp_dict = await state.get_data()
    a = list(map(lambda x: x.split("-"), temp_dict["money"].split("\n")))
    for i in a:
        f[i[0].strip()] = int(i[1].strip())
    collection.update_one(
        {"id": message.from_user.id}, {"$set": {"data.price_per_lesson": f}}
    )
    await message.answer(text="Цены сохранены.\n/help - для перехода в меню")
    await state.clear()


@router.message(Command(commands="schedule"))
async def process_schedule(message: Message, state: FSMContext):
    await message.answer(
        text="Вы хотите изменить или посмотреть расписание?",
        reply_markup=create_schedule_keyboard(
            "change schedule", "see the schedule"
        ),
    )
    await state.clear()


@router.callback_query(F.data == "see the schedule")
async def process_see_schedule(callback: CallbackQuery, state: FSMContext):
    a = collection.find_one({"id": callback.from_user.id})["data"]["schedule"]
    text = ""
    for key, value in a.items():
        text = f"{text}<b>{key}</b>\n"
        for name, time1 in sorted(
                value.items(),
                key=lambda item: datetime.strptime(item[1], "%H:%M").time(),
        ):
            text = f"{text}<i>{time1} - {name}</i>\n"
    await callback.message.edit_text(
        text=text.strip(),
        reply_markup=create_schedule_keyboard("change schedule", "cancel"),
    )
    await callback.answer()
    await state.clear()


@router.callback_query(F.data == "change schedule", StateFilter(default_state))
async def process_change_schedule(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="<b>Выберите день недели:</b>",
        reply_markup=create_schedule_keyboard(
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
            "cancel",
        ),
    )
    await state.set_state(Student.day)


@router.callback_query(StateFilter(Student.day))
async def process_add_or_remove(callback: CallbackQuery, state: FSMContext):
    key = LEXICON[callback.data]
    await state.update_data(day=key)
    a = collection.find_one({"id": callback.from_user.id})["data"]["schedule"]
    await callback.message.answer(f"<b>{key}</b>:")
    a = a[key]
    text = ""
    for name, time1 in sorted(
            a.items(), key=lambda item: datetime.strptime(item[1], "%H:%M").time()
    ):
        text = f"{text}{time1} - {name}\n"
    text = "<i>" + text + "</i>"
    await callback.message.answer(text)
    await callback.message.answer(
        text=f"Напишите свое расписание в формате:\n<i>12:00 - Имя1 Фамилия1\n14:00 - Имя2 Фамилия2</i>"
    )
    await state.set_state(Student.text)


@router.message(StateFilter(Student.text))
async def process_input_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    temp_dict1 = await state.get_data()
    temp_dict = temp_dict1["text"].split("\n")
    t = {}
    for i in temp_dict:
        j = list(map(lambda x: x.strip(), i.split("-")))
        t[j[1]] = j[0]

    collection.update_one(
        {"id": message.from_user.id},
        {"$set": {f'data.schedule.{temp_dict1["day"]}': t}},
    )
    await message.answer(
        text="<b>Расписание сохранено!\nВыберите следующий день недели или вернитесь в главное меню</b>",
        reply_markup=create_schedule_keyboard(
            "change schedule", "see the schedule", "cancel"
        ),
    )
    await state.clear()
