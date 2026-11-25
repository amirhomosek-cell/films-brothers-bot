"""Состояния FSM для сценариев администратора."""

from aiogram.fsm.state import State, StatesGroup


class AddMovie(StatesGroup):
    waiting_title = State()
    waiting_extra = State()
    waiting_poster = State()
    waiting_code = State()


class EditMovie(StatesGroup):
    waiting_value = State()
    waiting_poster = State()


class Broadcast(StatesGroup):
    waiting_message = State()
    confirm = State()


class AddChannel(StatesGroup):
    waiting_channel = State()


class SetAdmin(StatesGroup):
    waiting_user = State()
