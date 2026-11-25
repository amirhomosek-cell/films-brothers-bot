"""Тесты главных админов из бота: база, права, клавиатуры и обработчики кнопок."""

from __future__ import annotations

import asyncio
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.access import is_admin, is_env_owner, is_owner
from bot.config import Config
from bot.db import Database
from bot.handlers import admin_manage as am
from bot.keyboards import admin_card_keyboard, admins_menu_keyboard
from bot.states import SetAdmin
from bot.texts import t

OWNER = 11      # из ADMIN_IDS
DB_OWNER = 22   # главный из базы
ADMIN = 33      # обычный админ
STRANGER = 44


def _callbacks(markup) -> list[str]:
    return [b.callback_data for row in markup.inline_keyboard for b in row if b.callback_data]


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)  # последним: на Windows открытую базу не удалить
        self.db = Database(Path(self.tmp.name) / "roles.db")
        self.cfg = Config(bot_token="", admin_ids=frozenset({OWNER}), db_path=Path("x"))

    def tearDown(self) -> None:
        self.db.close()


class RoleDbTests(_Base):
    def test_set_admin_role_create_promote_demote(self) -> None:
        self.assertTrue(self.db.set_admin_role(ADMIN, owner=False, added_by=OWNER))
        self.assertTrue(self.db.is_db_admin(ADMIN))
        self.assertFalse(self.db.is_db_owner(ADMIN))
        self.assertFalse(self.db.set_admin_role(ADMIN, owner=False))
        self.assertTrue(self.db.set_admin_role(ADMIN, owner=True))
        self.assertTrue(self.db.is_db_owner(ADMIN))
        self.assertFalse(self.db.set_admin_role(ADMIN, owner=True))
        self.assertTrue(self.db.set_admin_role(ADMIN, owner=False))
        self.assertFalse(self.db.is_db_owner(ADMIN))
        self.assertTrue(self.db.is_db_admin(ADMIN))
        with self.assertRaises(ValueError):
            self.db.set_admin_role(0, owner=True)

    def test_new_owner_directly_and_remove(self) -> None:
        self.db.set_admin_role(DB_OWNER, owner=True, added_by=OWNER, username="@boss")
        self.assertTrue(self.db.is_db_owner(DB_OWNER))
        self.assertTrue(self.db.remove_db_admin(DB_OWNER))
        self.assertFalse(self.db.is_db_admin(DB_OWNER))
        self.assertFalse(self.db.is_db_owner(DB_OWNER))

    def test_list_admins_marks_db_owner_and_env_owner(self) -> None:
        self.db.add_admin(ADMIN, added_by=OWNER)
        self.db.add_admin(DB_OWNER, added_by=OWNER, is_owner=True)
        by_id = {a.user_id: a for a in self.db.list_admins({OWNER})}
        self.assertTrue(by_id[OWNER].is_owner and by_id[OWNER].env_owner)
        self.assertTrue(by_id[DB_OWNER].is_owner)
        self.assertFalse(by_id[DB_OWNER].env_owner)
        self.assertFalse(by_id[ADMIN].is_owner)
        order = [a.user_id for a in self.db.list_admins({OWNER})]
        self.assertEqual(order, [OWNER, DB_OWNER, ADMIN])

    def test_migration_adds_is_owner_and_keeps_admins(self) -> None:
        path = Path(self.tmp.name) / "old.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE admins (user_id INTEGER PRIMARY KEY, added_by INTEGER,"
            " added_at TEXT NOT NULL, username TEXT)"
        )
        conn.execute(
            "INSERT INTO admins VALUES (563245011, 6036662209, '2026-11-24', 'BakhtiyarTayirov')"
        )
        conn.commit()
        conn.close()
        db = Database(path)
        self.addCleanup(db.close)
        cols = {r["name"] for r in db.execute("PRAGMA table_info(admins)")}
        self.assertIn("is_owner", cols)
        self.assertTrue(db.is_db_admin(563245011))
        self.assertFalse(db.is_db_owner(563245011))
        listed = db.list_admins(())
        self.assertEqual(listed[0].username, "BakhtiyarTayirov")
        # повторное открытие не ломает базу
        db.close()
        db2 = Database(path)
        self.addCleanup(db2.close)
        self.assertTrue(db2.is_db_admin(563245011))


class RoleAccessTests(_Base):
    def test_is_owner_env_or_db(self) -> None:
        self.db.add_admin(ADMIN)
        self.db.add_admin(DB_OWNER, is_owner=True)
        self.assertTrue(is_owner(self.cfg, self.db, OWNER))
        self.assertTrue(is_owner(self.cfg, self.db, DB_OWNER))
        self.assertFalse(is_owner(self.cfg, self.db, ADMIN))
        self.assertFalse(is_owner(self.cfg, self.db, None))
        self.assertTrue(is_env_owner(self.cfg, OWNER))
        self.assertFalse(is_env_owner(self.cfg, DB_OWNER))
        self.assertTrue(is_admin(self.cfg, self.db, DB_OWNER))

    def test_plan_role_change(self) -> None:
        self.db.add_admin(ADMIN)
        self.db.add_admin(DB_OWNER, is_owner=True)
        plan = lambda uid, role: am.plan_role_change(self.cfg, self.db, uid, role)  # noqa: E731
        self.assertEqual(plan(OWNER, "admin"), "owner_env_protected")
        self.assertEqual(plan(OWNER, "owner"), "owner_env_protected")
        self.assertEqual(plan(STRANGER, "admin"), "addadmin_confirm")
        self.assertEqual(plan(STRANGER, "owner"), "setowner_confirm")
        self.assertEqual(plan(ADMIN, "admin"), "addadmin_already")
        self.assertEqual(plan(ADMIN, "owner"), "setowner_confirm")
        self.assertEqual(plan(DB_OWNER, "owner"), "addadmin_already_owner")
        self.assertEqual(plan(DB_OWNER, "admin"), "demote_confirm")


class RoleKeyboardTests(_Base):
    def test_owner_sees_buttons_non_owner_does_not(self) -> None:
        self.db.add_admin(ADMIN)
        self.db.add_admin(DB_OWNER, is_owner=True)
        admins = self.db.list_admins({OWNER})
        kb = admins_menu_keyboard("ru", admins, owner=True)
        cbs = _callbacks(kb)
        self.assertIn("adm:new:admin", cbs)
        self.assertIn("adm:new:owner", cbs)
        self.assertIn(f"adm:card:{ADMIN}", cbs)
        self.assertIn(f"adm:card:{DB_OWNER}", cbs)
        self.assertNotIn(f"adm:card:{OWNER}", cbs)
        texts = [b.text for row in kb.inline_keyboard for b in row]
        self.assertIn(t("ru", "btn_make_admin"), texts)
        self.assertIn(t("ru", "btn_make_owner"), texts)
        self.assertTrue(any(x.startswith("⭐") and str(DB_OWNER) in x for x in texts))
        plain = _callbacks(admins_menu_keyboard("uz", admins, owner=False))
        self.assertEqual(plain, ["panel:home"])

    def test_card_keyboard(self) -> None:
        self.assertIn(f"adm:set:owner:{ADMIN}", _callbacks(admin_card_keyboard("ru", ADMIN, is_owner=False)))
        cbs = _callbacks(admin_card_keyboard("ru", DB_OWNER, is_owner=True))
        self.assertIn(f"adm:set:admin:{DB_OWNER}", cbs)
        self.assertIn(f"adm:del:{DB_OWNER}", cbs)

    def test_admins_text_marks_db_owner(self) -> None:
        self.db.add_admin(DB_OWNER, is_owner=True, username="boss")
        self.db.add_admin(ADMIN, username="mod")
        text = am.admins_text(self.db, self.cfg, "ru", owner=True)
        self.assertIn("⭐ @boss", text)
        self.assertIn("• @mod", text)
        self.assertIn(t("ru", "admins_manage_hint"), text)
        self.assertNotIn(t("ru", "admins_manage_hint"), am.admins_text(self.db, self.cfg, "ru"))


def _callback(data: str, from_id: int = OWNER):
    cb = MagicMock()
    cb.data = data
    cb.from_user = SimpleNamespace(id=from_id)
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.bot = MagicMock()
    cb.bot.send_message = AsyncMock()
    return cb


def _message(text: str):
    msg = MagicMock()
    msg.text = text
    msg.caption = None
    msg.reply_to_message = None
    msg.forward_origin = None
    msg.forward_from = None
    msg.answer = AsyncMock()
    return msg


class _State:
    def __init__(self) -> None:
        self.state = None
        self.data: dict = {}

    async def set_state(self, value) -> None:
        self.state = value.state if hasattr(value, "state") else value

    async def get_state(self):
        return self.state

    async def update_data(self, **kw) -> None:
        self.data.update(kw)

    async def get_data(self) -> dict:
        return dict(self.data)

    async def clear(self) -> None:
        self.state = None
        self.data = {}


def run(coro):
    return asyncio.run(coro)


class RoleHandlerTests(_Base):
    def _ctx(self, owner: bool = True, admin: bool = True) -> dict:
        return dict(is_admin=admin, is_owner=owner, db=self.db, config=self.cfg, lang="ru")

    def test_non_owner_rejected_everywhere(self) -> None:
        self.db.add_admin(ADMIN)
        for data, handler in (
            (f"adm:set:owner:{ADMIN}", am.cb_admin_set_role),
            (f"adm:card:{ADMIN}", am.cb_admin_card),
            (f"adm:del:{ADMIN}", am.cb_admin_del),
        ):
            cb = _callback(data, from_id=ADMIN)
            run(handler(cb, **self._ctx(owner=False)))
            cb.answer.assert_awaited_with(t("ru", "owner_only"), show_alert=True)
        cb = _callback("adm:new:owner", from_id=ADMIN)
        state = _State()
        run(am.cb_admin_new(cb, state=state, is_admin=True, is_owner=False, lang="ru"))
        cb.answer.assert_awaited_with(t("ru", "owner_only"), show_alert=True)
        self.assertIsNone(state.state)
        self.assertFalse(self.db.is_db_owner(ADMIN))

    def test_make_owner_flow_by_id(self) -> None:
        state = _State()
        cb = _callback("adm:new:owner")
        run(am.cb_admin_new(cb, state=state, is_admin=True, is_owner=True, lang="ru"))
        self.assertEqual(state.state, SetAdmin.waiting_user.state)
        self.assertEqual(state.data["role"], "owner")
        cb.message.answer.assert_awaited_with(t("ru", "setadmin_ask_owner"))

        msg = _message(str(STRANGER))
        run(am.setadmin_got_user(msg, state=state, **self._ctx()))
        self.assertIsNone(state.state)
        args, kwargs = msg.answer.await_args
        self.assertIn(str(STRANGER), args[0])
        self.assertIn(f"adm:set:owner:{STRANGER}", _callbacks(kwargs["reply_markup"]))

        cb2 = _callback(f"adm:set:owner:{STRANGER}")
        run(am.cb_admin_set_role(cb2, **self._ctx()))
        self.assertTrue(self.db.is_db_owner(STRANGER))
        self.assertTrue(is_owner(self.cfg, self.db, STRANGER))
        cb2.bot.send_message.assert_awaited()
        self.assertIn("⭐", cb2.message.edit_text.await_args.args[0])

    def test_make_admin_then_promote_demote_remove(self) -> None:
        cb = _callback(f"adm:set:admin:{STRANGER}")
        run(am.cb_admin_set_role(cb, **self._ctx()))
        self.assertTrue(self.db.is_db_admin(STRANGER))
        self.assertFalse(self.db.is_db_owner(STRANGER))

        run(am.cb_admin_set_role(_callback(f"adm:set:owner:{STRANGER}"), **self._ctx()))
        self.assertTrue(self.db.is_db_owner(STRANGER))

        card = _callback(f"adm:card:{STRANGER}")
        run(am.cb_admin_card(card, **self._ctx()))
        markup = card.message.edit_text.await_args.kwargs["reply_markup"]
        self.assertIn(f"adm:set:admin:{STRANGER}", _callbacks(markup))

        demote = _callback(f"adm:set:admin:{STRANGER}")
        run(am.cb_admin_set_role(demote, **self._ctx()))
        self.assertFalse(self.db.is_db_owner(STRANGER))
        self.assertTrue(self.db.is_db_admin(STRANGER))
        demote.bot.send_message.assert_not_awaited()

        delete = _callback(f"adm:del:{STRANGER}")
        run(am.cb_admin_del(delete, **self._ctx()))
        markup = delete.message.edit_text.await_args.kwargs["reply_markup"]
        self.assertIn(f"deladmin:yes:{STRANGER}", _callbacks(markup))
        run(am.cb_deladmin_yes(_callback(f"deladmin:yes:{STRANGER}"), **self._ctx()))
        self.assertFalse(self.db.is_db_admin(STRANGER))

    def test_db_owner_can_remove_other_db_owner(self) -> None:
        self.db.add_admin(DB_OWNER, is_owner=True)
        self.db.add_admin(ADMIN, is_owner=True)
        run(am.cb_deladmin_yes(_callback(f"deladmin:yes:{ADMIN}", from_id=DB_OWNER), **self._ctx()))
        self.assertFalse(self.db.is_db_admin(ADMIN))

    def test_env_owner_protected(self) -> None:
        for data, handler in (
            (f"adm:set:admin:{OWNER}", am.cb_admin_set_role),
            (f"adm:set:owner:{OWNER}", am.cb_admin_set_role),
        ):
            cb = _callback(data, from_id=DB_OWNER)
            run(handler(cb, **self._ctx()))
            self.assertEqual(cb.message.edit_text.await_args.args[0], t("ru", "owner_env_protected"))
        for handler, prefix in ((am.cb_admin_card, "adm:card"), (am.cb_admin_del, "adm:del")):
            cb = _callback(f"{prefix}:{OWNER}", from_id=DB_OWNER)
            run(handler(cb, **self._ctx()))
            cb.answer.assert_awaited_with(t("ru", "owner_env_protected"), show_alert=True)
        cb = _callback(f"deladmin:yes:{OWNER}", from_id=DB_OWNER)
        run(am.cb_deladmin_yes(cb, **self._ctx()))
        self.assertEqual(cb.message.edit_text.await_args.args[0], t("ru", "deladmin_owner"))
        self.assertEqual(self.db.list_admins(())[:1], [])

    def test_input_errors_keep_waiting(self) -> None:
        state = _State()
        run(state.set_state(SetAdmin.waiting_user))
        run(state.update_data(role="admin"))
        msg = _message("not valid!!")
        run(am.setadmin_got_user(msg, state=state, **self._ctx()))
        msg.answer.assert_awaited_with(t("ru", "addadmin_invalid"))
        self.assertEqual(state.state, SetAdmin.waiting_user.state)
        msg = _message("@nobody_here")
        run(am.setadmin_got_user(msg, state=state, **self._ctx()))
        msg.answer.assert_awaited_with(t("ru", "addadmin_username_not_found", username="nobody_here"))

    def test_username_input_and_already_states(self) -> None:
        self.db.upsert_user(STRANGER, username="ali_user", first_name="Ali")
        self.db.add_admin(STRANGER)
        state = _State()
        run(state.set_state(SetAdmin.waiting_user))
        run(state.update_data(role="admin"))
        msg = _message("@ali_user")
        run(am.setadmin_got_user(msg, state=state, **self._ctx()))
        self.assertEqual(msg.answer.await_args.args[0], t("ru", "addadmin_already"))
        run(state.set_state(SetAdmin.waiting_user))
        run(state.update_data(role="owner"))
        msg = _message("@ali_user")
        run(am.setadmin_got_user(msg, state=state, **self._ctx()))
        self.assertIn(f"adm:set:owner:{STRANGER}", _callbacks(msg.answer.await_args.kwargs["reply_markup"]))

    def test_non_owner_input_rejected(self) -> None:
        state = _State()
        run(state.set_state(SetAdmin.waiting_user))
        msg = _message(str(STRANGER))
        run(am.setadmin_got_user(msg, state=state, **self._ctx(owner=False)))
        msg.answer.assert_awaited_with(t("ru", "owner_only"))
        self.assertFalse(self.db.is_db_admin(STRANGER))

    def test_panel_admins_shows_buttons_only_to_owner(self) -> None:
        cb = _callback("panel:admins")
        run(am.cb_panel_admins(cb, **self._ctx()))
        self.assertIn("adm:new:owner", _callbacks(cb.message.edit_text.await_args.kwargs["reply_markup"]))
        cb = _callback("panel:admins", from_id=ADMIN)
        run(am.cb_panel_admins(cb, **self._ctx(owner=False)))
        self.assertNotIn("adm:new:owner", _callbacks(cb.message.edit_text.await_args.kwargs["reply_markup"]))


if __name__ == "__main__":
    unittest.main()
