"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.access import display_name
from bot.db import AdminInfo, Channel
from bot.texts import t


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("ru", "btn_ru"), callback_data="lang:ru"),
                InlineKeyboardButton(text=t("uz", "btn_uz"), callback_data="lang:uz"),
            ]
        ]
    )


def skip_keyboard(lang: str, callback: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data=callback)]
        ]
    )


def use_code_keyboard(lang: str, code: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_use_code", code=code),
                    callback_data=f"usecode:{code}",
                )
            ],
            [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel")],
        ]
    )


def confirm_delete_keyboard(lang: str, code: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_yes_del"), callback_data=f"del:{code}"
                ),
                InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"),
            ]
        ]
    )


def edit_menu_keyboard(lang: str, code: int) -> InlineKeyboardMarkup:
    def btn(key: str, field: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=t(lang, key), callback_data=f"edit:{code}:{field}")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn("btn_edit_title", "title"), btn("btn_edit_year", "year")],
            [btn("btn_edit_genre", "genre"), btn("btn_edit_description", "description")],
            [btn("btn_edit_code", "code"), btn("btn_edit_poster", "poster")],
            [InlineKeyboardButton(text=t(lang, "btn_done"), callback_data="cancel")],
        ]
    )


def list_keyboard(lang: str, page: int, pages: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"list:{page - 1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=t(lang, "btn_panel_back"), callback_data="panel:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_broadcast_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_broadcast"), callback_data="broadcast:yes"
                ),
                InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"),
            ]
        ]
    )


def subscription_keyboard(lang: str, channels: list[Channel]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for ch in channels:
        title = ch.title or ch.chat_id
        label = t(lang, "btn_channel", title=title)
        if ch.url:
            rows.append([InlineKeyboardButton(text=label, url=ch.url)])
        else:
            # Без ссылки всё равно показываем название, проверка идёт по id.
            rows.append(
                [InlineKeyboardButton(text=label, callback_data=f"chinfo:{ch.id}")]
            )
    rows.append(
        [InlineKeyboardButton(text=t(lang, "btn_check_sub"), callback_data="checksub")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channels_menu_keyboard(lang: str, channels: list[Channel], enabled: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=t(lang, "btn_ch_add"), callback_data="ch:add")],
        [
            InlineKeyboardButton(
                text=t(lang, "btn_ch_toggle_off" if enabled else "btn_ch_toggle_on"),
                callback_data="ch:toggle",
            )
        ],
    ]
    for ch in channels:
        title = (ch.title or ch.chat_id)[:40]
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_ch_remove", title=title),
                    callback_data=f"ch:rm:{ch.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "btn_panel_back"), callback_data="panel:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_entry_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_admin_panel"), callback_data="panel:home")]
        ]
    )


def admin_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_panel_list"), callback_data="panel:list"),
                InlineKeyboardButton(text=t(lang, "btn_panel_stats"), callback_data="panel:stats"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_panel_channels"), callback_data="panel:channels"),
                InlineKeyboardButton(text=t(lang, "btn_panel_admins"), callback_data="panel:admins"),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_panel_broadcast"), callback_data="panel:broadcast"
                )
            ],
        ]
    )


def back_to_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_panel_back"), callback_data="panel:home")]
        ]
    )


def confirm_add_admin_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_yes_addadmin"),
                    callback_data=f"addadmin:yes:{user_id}",
                ),
                InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"),
            ]
        ]
    )


def confirm_del_admin_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_yes_deladmin"),
                    callback_data=f"deladmin:yes:{user_id}",
                ),
                InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"),
            ]
        ]
    )


def poster_keyboard(lang: str, *, can_clear: bool = False, skip_callback: str = "add:skip_poster") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data=skip_callback)]
    ]
    if can_clear:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_clear_poster"), callback_data="edit:clear_poster")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)



def admins_menu_keyboard(lang: str, admins: list[AdminInfo], *, owner: bool) -> InlineKeyboardMarkup:
    """Раздел «Админы». Кнопки управления видят только главные админы."""
    rows: list[list[InlineKeyboardButton]] = []
    if owner:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_make_admin"), callback_data="adm:new:admin")]
        )
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_make_owner"), callback_data="adm:new:owner")]
        )
        for admin in admins:
            if admin.env_owner:
                continue  # главных из ADMIN_IDS менять нельзя
            mark = "⭐" if admin.is_owner else "👤"
            name = display_name(
                user_id=admin.user_id, first_name=admin.first_name, username=admin.username
            )
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{mark} {name}"[:60],
                        callback_data=f"adm:card:{admin.user_id}",
                    )
                ]
            )
    rows.append([InlineKeyboardButton(text=t(lang, "btn_panel_back"), callback_data="panel:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_card_keyboard(lang: str, user_id: int, *, is_owner: bool) -> InlineKeyboardMarkup:
    role_btn = (
        InlineKeyboardButton(text=t(lang, "btn_demote_owner"), callback_data=f"adm:set:admin:{user_id}")
        if is_owner
        else InlineKeyboardButton(text=t(lang, "btn_promote_owner"), callback_data=f"adm:set:owner:{user_id}")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [role_btn],
            [InlineKeyboardButton(text=t(lang, "btn_remove_admin"), callback_data=f"adm:del:{user_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_admins_back"), callback_data="panel:admins")],
        ]
    )


def confirm_set_role_keyboard(lang: str, user_id: int, role: str, yes_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, yes_key), callback_data=f"adm:set:{role}:{user_id}"
                ),
                InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"),
            ]
        ]
    )


def admins_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_admins_back"), callback_data="panel:admins")]
        ]
    )
