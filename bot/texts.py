"""Все пользовательские тексты бота: русский и узбекский (латиница)."""

from __future__ import annotations

from typing import Any

from bot.db import Movie

LANGS = ("ru", "uz")
DEFAULT_LANG = "ru"

# Подпись к видео не длиннее 1024 символов.
CAPTION_LIMIT = 1024

TEXTS: dict[str, dict[str, str]] = {
    "ru": {
        "btn_ru": "🇷🇺 Русский",
        "btn_uz": "🇺🇿 O'zbekcha",
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "lang_saved": "Язык сохранён: русский.",
        "help": (
            "Отправьте <b>код фильма</b> (только цифры) — и я пришлю его название.\n\n"
            "Команды:\n"
            "/start — начать и выбрать язык\n"
            "/lang — сменить язык\n"
            "/top — топ-10 фильмов по просмотрам\n"
            "/help — эта справка"
        ),
        "help_admin": (
            "\n\n<b>Команды администратора</b>\n"
            "/admin — панель администратора\n"
            "/add — добавить фильм\n"
            "/add Название — добавить с автокодом\n"
            "/add КОД Название — сразу, например /add 12 Интерстеллар\n"
            "/del КОД — удалить фильм\n"
            "/edit КОД — изменить данные или постер\n"
            "/list — список фильмов\n"
            "/top — топ-10 по просмотрам\n"
            "/stats — статистика\n"
            "/broadcast — рассылка всем пользователям\n"
            "/channels — обязательная подписка на каналы\n"
            "/admins — список администраторов\n"
            "/addadmin ID или @username — добавить администратора (только главный)\n"
            "/deladmin ID — удалить администратора (только главный)\n"
            "/cancel — отменить текущее действие"
        ),
        "send_code_hint": "Пришлите числовой код фильма, например: <b>12</b>",
        "movie_not_found": "Фильм с кодом <b>{code}</b> не найден.",
        "code_label": "Код",
        "sub_required": "Чтобы получить фильм, подпишитесь на каналы:",
        "sub_still_missing": "Вы ещё не подписаны на все каналы. Подпишитесь и нажмите кнопку ещё раз.",
        "sub_ok": "Подписка подтверждена. Отправьте код фильма ещё раз.",
        "btn_check_sub": "✅ Проверить подписку",
        "btn_channel": "📢 {title}",
        "top_title": "🏆 Топ-{n} фильмов по просмотрам:",
        "top_empty": "Пока нет фильмов.",
        "top_line": "{i}. Код {code} · 👁 {views}",
        "cancelled": "Действие отменено.",
        "nothing_to_cancel": "Сейчас нечего отменять.",
        # admin
        "admin_only": "Эта команда доступна только администратору.",
        "add_ask_title": "Отправьте <b>название</b> фильма. /cancel — отмена.",
        "add_ask_poster": "Можно прислать <b>постер</b> (фото) или нажмите «Пропустить».",
        "add_ask_extra": (
            "Название: <b>{title}</b>\n\n"
            "Отправьте дополнительные данные в формате:\n"
            "<code>год | жанр | описание</code>\n"
            "Любую часть можно заменить на «-».\n"
            "Или нажмите «Пропустить»."
        ),
        "add_ask_code": (
            "Следующий свободный код: <b>{code}</b>.\n"
            "Нажмите кнопку, чтобы использовать его, или отправьте свой код (число)."
        ),
        "add_code_taken": "Код <b>{code}</b> уже занят. Введите другой или нажмите кнопку.",
        "add_invalid_code": "Код должен быть целым числом больше 0.",
        "add_invalid_title": "Название не может быть пустым. Отправьте название фильма.",
        "add_no_title": "Сначала укажите название. Начните заново: /add",
        "add_done": "Фильм сохранён.\n\n🎬 <b>{title}</b>\n🔢 Код: <b>{code}</b>",
        "add_failed": "Не удалось сохранить фильм: {error}",
        "btn_skip": "Пропустить",
        "btn_use_code": "Использовать код {code}",
        "del_usage": "Укажите код: <code>/del 12</code>",
        "del_not_found": "Фильм с кодом <b>{code}</b> не найден.",
        "del_confirm": "Удалить фильм <b>{title}</b> (код {code})?",
        "del_done": "Фильм с кодом <b>{code}</b> удалён.",
        "btn_yes_del": "Да, удалить",
        "btn_cancel": "Отмена",
        "edit_usage": "Укажите код: <code>/edit 12</code>",
        "edit_not_found": "Фильм с кодом <b>{code}</b> не найден.",
        "edit_menu": (
            "Редактирование фильма <b>{code}</b>:\n"
            "🎬 {title}\n"
            "📅 {year}\n"
            "🎭 {genre}\n"
            "📝 {description}\n"
            "🖼 {poster}\n"
            "👁 {views}\n\n"
            "Выберите, что изменить."
        ),
        "edit_ask_title": "Отправьте новое название.",
        "edit_ask_year": "Отправьте год (число) или «-», чтобы очистить.",
        "edit_ask_genre": "Отправьте жанр или «-», чтобы очистить.",
        "edit_ask_description": "Отправьте описание или «-», чтобы очистить.",
        "edit_ask_code": "Отправьте новый код (число).",
        "edit_ask_poster": "Пришлите новое фото постера.",
        "edit_done": "Изменения сохранены.",
        "edit_code_taken": "Код <b>{code}</b> уже занят.",
        "btn_edit_title": "Название",
        "btn_edit_year": "Год",
        "btn_edit_genre": "Жанр",
        "btn_edit_description": "Описание",
        "btn_edit_code": "Код",
        "btn_edit_poster": "Постер",
        "btn_done": "Готово",
        "dash": "—",
        "list_empty": "В базе ещё нет фильмов.",
        "list_title": "Фильмы, стр. {page}/{pages} (всего {total}):",
        "list_line": "{code}. <b>{title}</b> · 👁 {views}",
        "btn_prev": "‹ Назад",
        "btn_next": "Вперёд ›",
        "stats": (
            "📊 <b>Статистика</b>\n\n"
            "👥 Пользователи: <b>{users}</b>\n"
            "🎞 Фильмы: <b>{movies}</b>\n"
            "🔎 Поисков: <b>{searches}</b> (найдено: {found})\n"
            "👁 Просмотров: <b>{total_views}</b>"
        ),
        "broadcast_send": "Отправьте сообщение, которое нужно разослать всем пользователям (текст, фото, видео и т.д.).",
        "broadcast_confirm": "Разослать это сообщение <b>{n}</b> пользователям?",
        "btn_broadcast": "Разослать",
        "broadcast_none": "Нет пользователей для рассылки.",
        "broadcast_progress": "Рассылка… {done}/{total}",
        "broadcast_done": "Рассылка завершена.\nДоставлено: <b>{ok}</b>\nНе доставлено: <b>{fail}</b>",
        "channels_menu": (
            "Обязательная подписка: <b>{status}</b>\n\n"
            "{list}\n\n"
            "Чтобы добавить канал, нажмите кнопку и пришлите @username или ID (например, <code>-100123…</code>).\n"
            "Бот должен быть администратором канала."
        ),
        "channels_empty": "Каналы пока не добавлены.",
        "channels_item": "• {title} (<code>{chat_id}</code>)",
        "channels_on": "включена",
        "channels_off": "выключена",
        "btn_ch_add": "Добавить канал",
        "btn_ch_toggle_on": "Включить проверку",
        "btn_ch_toggle_off": "Выключить проверку",
        "btn_ch_remove": "✖ {title}",
        "channels_add_ask": "Пришлите @username канала или его числовой ID. /cancel — отмена.",
        "channels_added": "Канал «{title}» добавлен.",
        "channels_add_fail": "Не удалось добавить канал: {error}",
        "channels_already": "Этот канал уже в списке.",
        "channels_removed": "Канал удалён.",
        "channels_toggled_on": "Проверка подписки включена.",
        "channels_toggled_off": "Проверка подписки выключена.",
        "channels_bot_not_admin": "Бот не является администратором этого канала или не имеет доступа.",
        "channels_invalid": "Не похоже на @username или ID канала.",
        "need_photo": "Пришлите фото постера или нажмите «Пропустить».",
        "btn_clear_poster": "Убрать постер",
        "poster_yes": "есть",
        "poster_no": "нет",
        "edit_poster_cleared": "Постер удалён.",
        "invalid_year": "Год должен быть числом (например, 2020) или «-».",
        "owner_only": "Добавлять и удалять администраторов может только главный администратор.",
        "admins_title": "👥 <b>Администраторы</b>",
        "admins_owner_line": "⭐ {name} — <code>{user_id}</code> · главный",
        "admins_line": "• {name} — <code>{user_id}</code>",
        "admins_empty": "Кроме главных, дополнительных администраторов нет.",
        "addadmin_usage": (
            "Укажите ID, @username (если человек уже нажимал /start) "
            "или ответьте / перешлите его сообщение.\n"
            "Пример: <code>/addadmin 123456789</code>"
        ),
        "addadmin_confirm": "Добавить администратора?\n\n{name}\nID: <code>{user_id}</code>",
        "addadmin_done": "{name} назначен администратором.",
        "addadmin_already": "Этот пользователь уже администратор.",
        "addadmin_already_owner": "Этот пользователь уже главный администратор.",
        "addadmin_invalid": "Некорректный ID или username.",
        "addadmin_username_not_found": (
            "Пользователь @{username} не найден. Он должен сначала написать боту /start, "
            "либо укажите числовой ID."
        ),
        "addadmin_hidden": "Telegram скрыл отправителя этого сообщения, ID недоступен. Укажите числовой ID.",
        "addadmin_bot": "Нельзя назначить бота администратором.",
        "addadmin_notify": "Вас назначили администратором этого бота. Откройте /help или /admin.",
        "addadmin_notify_fail": "Администратор добавлен, но бот не смог ему написать (нужно, чтобы он нажал /start).",
        "deladmin_usage": "Укажите ID: <code>/deladmin 123456789</code> или ответьте на сообщение пользователя.",
        "deladmin_confirm": "Снять права администратора у {name} (<code>{user_id}</code>)?",
        "deladmin_done": "{name} больше не администратор.",
        "deladmin_not_found": "Этот пользователь не является дополнительным администратором.",
        "deladmin_owner": "Главного администратора (из ADMIN_IDS) удалить нельзя.",
        "btn_yes_addadmin": "Да, добавить",
        "btn_yes_deladmin": "Да, снять права",
        "btn_admin_panel": "⚙️ Админ-панель",
        "admin_panel_title": "⚙️ <b>Админ-панель</b>\n\nВыберите раздел:",
        "btn_panel_list": "📋 Фильмы",
        "btn_panel_stats": "📊 Статистика",
        "btn_panel_channels": "📢 Каналы",
        "btn_panel_admins": "👥 Админы",
        "btn_panel_broadcast": "📣 Рассылка",
        "btn_panel_back": "‹ В панель",
    },
    "uz": {
        "btn_ru": "🇷🇺 Русский",
        "btn_uz": "🇺🇿 O'zbekcha",
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "lang_saved": "Til saqlandi: o'zbekcha.",
        "help": (
            "Film <b>kodini</b> yuboring (faqat raqamlar) — men uning nomini yuboraman.\n\n"
            "Buyruqlar:\n"
            "/start — boshlash va tilni tanlash\n"
            "/lang — tilni almashtirish\n"
            "/top — ko'rishlar bo'yicha top-10\n"
            "/help — ushbu yordam"
        ),
        "help_admin": (
            "\n\n<b>Administrator buyruqlari</b>\n"
            "/admin — administrator paneli\n"
            "/add — film qo'shish\n"
            "/add Nomi — avtokod bilan qo'shish\n"
            "/add KOD Nomi — darhol, masalan /add 12 Interstellar\n"
            "/del KOD — filmni o'chirish\n"
            "/edit KOD — ma'lumot yoki posterni o'zgartirish\n"
            "/list — filmlar ro'yxati\n"
            "/top — ko'rishlar bo'yicha top-10\n"
            "/stats — statistika\n"
            "/broadcast — barcha foydalanuvchilarga xabar\n"
            "/channels — kanallarga majburiy obuna\n"
            "/admins — administratorlar ro'yxati\n"
            "/addadmin ID yoki @username — administrator qo'shish (faqat asosiy)\n"
            "/deladmin ID — administratorni o'chirish (faqat asosiy)\n"
            "/cancel — joriy amalni bekor qilish"
        ),
        "send_code_hint": "Filmning raqamli kodini yuboring, masalan: <b>12</b>",
        "movie_not_found": "<b>{code}</b> kodli film topilmadi.",
        "code_label": "Kod",
        "sub_required": "Filmni olish uchun kanallarga obuna bo'ling:",
        "sub_still_missing": "Siz hali barcha kanallarga obuna bo'lmagansiz. Obuna bo'ling va tugmani qayta bosing.",
        "sub_ok": "Obuna tasdiqlandi. Film kodini yana yuboring.",
        "btn_check_sub": "✅ Obunani tekshirish",
        "btn_channel": "📢 {title}",
        "top_title": "🏆 Ko'rishlar bo'yicha top-{n}:",
        "top_empty": "Hozircha filmlar yo'q.",
        "top_line": "{i}. Kod {code} · 👁 {views}",
        "cancelled": "Amal bekor qilindi.",
        "nothing_to_cancel": "Hozir bekor qiladigan narsa yo'q.",
        "admin_only": "Bu buyruq faqat administrator uchun.",
        "add_ask_title": "Filmning <b>nomini</b> yuboring. /cancel — bekor qilish.",
        "add_ask_poster": "<b>Posterni</b> (rasm) yuborishingiz mumkin yoki «O'tkazib yuborish»ni bosing.",
        "add_ask_extra": (
            "Nomi: <b>{title}</b>\n\n"
            "Qo'shimcha ma'lumotni shu formatda yuboring:\n"
            "<code>yil | janr | tavsif</code>\n"
            "Istalgan qismini «-» bilan almashtirish mumkin.\n"
            "Yoki «O'tkazib yuborish»ni bosing."
        ),
        "add_ask_code": (
            "Keyingi bo'sh kod: <b>{code}</b>.\n"
            "Undan foydalanish uchun tugmani bosing yoki o'z kodingizni (raqam) yuboring."
        ),
        "add_code_taken": "<b>{code}</b> kodi band. Boshqa kod kiriting yoki tugmani bosing.",
        "add_invalid_code": "Kod 0 dan katta butun son bo'lishi kerak.",
        "add_invalid_title": "Nom bo'sh bo'lishi mumkin emas. Film nomini yuboring.",
        "add_no_title": "Avval nomini yozing. Qaytadan boshlang: /add",
        "add_done": "Film saqlandi.\n\n🎬 <b>{title}</b>\n🔢 Kod: <b>{code}</b>",
        "add_failed": "Filmni saqlab bo'lmadi: {error}",
        "btn_skip": "O'tkazib yuborish",
        "btn_use_code": "Kod {code} dan foydalanish",
        "del_usage": "Kodni yozing: <code>/del 12</code>",
        "del_not_found": "<b>{code}</b> kodli film topilmadi.",
        "del_confirm": "<b>{title}</b> filmini (kod {code}) o'chirilsinmi?",
        "del_done": "<b>{code}</b> kodli film o'chirildi.",
        "btn_yes_del": "Ha, o'chirish",
        "btn_cancel": "Bekor qilish",
        "edit_usage": "Kodni yozing: <code>/edit 12</code>",
        "edit_not_found": "<b>{code}</b> kodli film topilmadi.",
        "edit_menu": (
            "<b>{code}</b> kodli filmni tahrirlash:\n"
            "🎬 {title}\n"
            "📅 {year}\n"
            "🎭 {genre}\n"
            "📝 {description}\n"
            "🖼 {poster}\n"
            "👁 {views}\n\n"
            "Nimani o'zgartirishni tanlang."
        ),
        "edit_ask_title": "Yangi nomni yuboring.",
        "edit_ask_year": "Yilni (raqam) yuboring yoki tozalash uchun «-».",
        "edit_ask_genre": "Janrni yuboring yoki tozalash uchun «-».",
        "edit_ask_description": "Tavsifni yuboring yoki tozalash uchun «-».",
        "edit_ask_code": "Yangi kodni (raqam) yuboring.",
        "edit_ask_poster": "Yangi poster rasmini yuboring.",
        "edit_done": "O'zgarishlar saqlandi.",
        "edit_code_taken": "<b>{code}</b> kodi band.",
        "btn_edit_title": "Nomi",
        "btn_edit_year": "Yili",
        "btn_edit_genre": "Janri",
        "btn_edit_description": "Tavsifi",
        "btn_edit_code": "Kodi",
        "btn_edit_poster": "Poster",
        "btn_done": "Tayyor",
        "dash": "—",
        "list_empty": "Bazada hozircha filmlar yo'q.",
        "list_title": "Filmlar, {page}/{pages} sahifa (jami {total}):",
        "list_line": "{code}. <b>{title}</b> · 👁 {views}",
        "btn_prev": "‹ Orqaga",
        "btn_next": "Oldinga ›",
        "stats": (
            "📊 <b>Statistika</b>\n\n"
            "👥 Foydalanuvchilar: <b>{users}</b>\n"
            "🎞 Filmlar: <b>{movies}</b>\n"
            "🔎 Qidiruvlar: <b>{searches}</b> (topildi: {found})\n"
            "👁 Ko'rishlar: <b>{total_views}</b>"
        ),
        "broadcast_send": "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring (matn, rasm, video va hokazo).",
        "broadcast_confirm": "Bu xabar <b>{n}</b> foydalanuvchiga yuborilsinmi?",
        "btn_broadcast": "Yuborish",
        "broadcast_none": "Xabar yuboriladigan foydalanuvchilar yo'q.",
        "broadcast_progress": "Yuborilmoqda… {done}/{total}",
        "broadcast_done": "Yuborish yakunlandi.\nYetkazildi: <b>{ok}</b>\nYetkazilmadi: <b>{fail}</b>",
        "channels_menu": (
            "Majburiy obuna: <b>{status}</b>\n\n"
            "{list}\n\n"
            "Kanal qo'shish uchun tugmani bosing va @username yoki ID ni yuboring (masalan, <code>-100123…</code>).\n"
            "Bot kanalda administrator bo'lishi kerak."
        ),
        "channels_empty": "Kanallar hali qo'shilmagan.",
        "channels_item": "• {title} (<code>{chat_id}</code>)",
        "channels_on": "yoqilgan",
        "channels_off": "o'chirilgan",
        "btn_ch_add": "Kanal qo'shish",
        "btn_ch_toggle_on": "Tekshiruvni yoqish",
        "btn_ch_toggle_off": "Tekshiruvni o'chirish",
        "btn_ch_remove": "✖ {title}",
        "channels_add_ask": "Kanal @username yoki raqamli ID sini yuboring. /cancel — bekor qilish.",
        "channels_added": "«{title}» kanali qo'shildi.",
        "channels_add_fail": "Kanalni qo'shib bo'lmadi: {error}",
        "channels_already": "Bu kanal allaqachon ro'yxatda.",
        "channels_removed": "Kanal o'chirildi.",
        "channels_toggled_on": "Obuna tekshiruvi yoqildi.",
        "channels_toggled_off": "Obuna tekshiruvi o'chirildi.",
        "channels_bot_not_admin": "Bot bu kanalda administrator emas yoki unga kira olmaydi.",
        "channels_invalid": "Bu @username yoki kanal ID siga o'xshamadi.",
        "need_photo": "Poster rasmini yuboring yoki «O'tkazib yuborish»ni bosing.",
        "btn_clear_poster": "Posterni olib tashlash",
        "poster_yes": "bor",
        "poster_no": "yo'q",
        "edit_poster_cleared": "Poster o'chirildi.",
        "invalid_year": "Yil raqam bo'lishi kerak (masalan, 2020) yoki «-».",
        "owner_only": "Administratorlarni faqat asosiy administrator qo'shishi va o'chirishi mumkin.",
        "admins_title": "👥 <b>Administratorlar</b>",
        "admins_owner_line": "⭐ {name} — <code>{user_id}</code> · asosiy",
        "admins_line": "• {name} — <code>{user_id}</code>",
        "admins_empty": "Asosiylardan tashqari qo'shimcha administratorlar yo'q.",
        "addadmin_usage": (
            "ID, @username (agar odam allaqachon /start bosgan bo'lsa) "
            "yuboring yoki uning xabariga javob / forward qiling.\n"
            "Masalan: <code>/addadmin 123456789</code>"
        ),
        "addadmin_confirm": "Administrator qo'shilsinmi?\n\n{name}\nID: <code>{user_id}</code>",
        "addadmin_done": "{name} administrator etib tayinlandi.",
        "addadmin_already": "Bu foydalanuvchi allaqachon administrator.",
        "addadmin_already_owner": "Bu foydalanuvchi allaqachon asosiy administrator.",
        "addadmin_invalid": "ID yoki username noto'g'ri.",
        "addadmin_username_not_found": (
            "@{username} foydalanuvchisi topilmadi. Avval u botga /start yozishi kerak, "
            "yoki raqamli ID ni kiriting."
        ),
        "addadmin_hidden": "Telegram bu xabar yuboruvchisini yashirdi, ID mavjud emas. Raqamli ID ni kiriting.",
        "addadmin_bot": "Botni administrator qilib bo'lmaydi.",
        "addadmin_notify": "Siz ushbu bot administratori etib tayinlandingiz. /help yoki /admin ni oching.",
        "addadmin_notify_fail": "Administrator qo'shildi, lekin bot unga yoza olmadi (u /start bosishi kerak).",
        "deladmin_usage": "ID ni yozing: <code>/deladmin 123456789</code> yoki foydalanuvchi xabariga javob bering.",
        "deladmin_confirm": "{name} (<code>{user_id}</code>) dan administrator huquqi olinsinmi?",
        "deladmin_done": "{name} endi administrator emas.",
        "deladmin_not_found": "Bu foydalanuvchi qo'shimcha administrator emas.",
        "deladmin_owner": "Asosiy administratorni (ADMIN_IDS dagi) o'chirib bo'lmaydi.",
        "btn_yes_addadmin": "Ha, qo'shish",
        "btn_yes_deladmin": "Ha, huquqni olish",
        "btn_admin_panel": "⚙️ Admin-panel",
        "admin_panel_title": "⚙️ <b>Admin-panel</b>\n\nBo'limni tanlang:",
        "btn_panel_list": "📋 Filmlar",
        "btn_panel_stats": "📊 Statistika",
        "btn_panel_channels": "📢 Kanallar",
        "btn_panel_admins": "👥 Adminlar",
        "btn_panel_broadcast": "📣 Xabar yuborish",
        "btn_panel_back": "‹ Panelga",
    },
}


def t(lang: str | None, key: str, **kwargs: Any) -> str:
    lang = lang if lang in TEXTS else DEFAULT_LANG
    text = TEXTS[lang].get(key) or TEXTS[DEFAULT_LANG].get(key) or key
    if kwargs:
        return text.format(**kwargs)
    return text


def format_movie_text(
    lang: str | None,
    movie: Movie,
    *,
    views: int | None = None,
    include_views: bool = False,
    limit: int | None = None,
) -> str:
    """Текст карточки фильма: название (главное), код, год/жанр/описание."""
    lang = lang if lang in TEXTS else DEFAULT_LANG
    view_count = movie.views if views is None else views
    description = movie.description

    def _build(desc: str | None) -> str:
        lines = [
            f"🎬 <b>{movie.title}</b>",
            f"🔢 {t(lang, 'code_label')}: {movie.code}",
        ]
        if movie.year:
            lines.append(f"📅 {movie.year}")
        if movie.genre:
            lines.append(f"🎭 {movie.genre}")
        if desc:
            lines.append("")
            lines.append(desc)
        if include_views:
            lines.append("")
            lines.append(f"👁 {view_count}")
        return "\n".join(lines)

    cap_limit = CAPTION_LIMIT if limit is None else limit
    caption = _build(description)
    if len(caption) <= cap_limit:
        return caption
    if description:
        overhead = len(caption) - len(description)
        keep = max(0, cap_limit - overhead - 1)
        caption = _build(description[:keep].rstrip() + "…")
    if len(caption) > cap_limit:
        return caption[: cap_limit - 1] + "…"
    return caption


def format_caption(lang: str | None, movie: Movie, *, views: int | None = None) -> str:
    """Совместимый алиас: карточка с просмотрами, лимит как у подписи к фото."""
    return format_movie_text(
        lang, movie, views=views, include_views=True, limit=CAPTION_LIMIT
    )


def parse_extra(text: str) -> dict[str, Any]:
    """Разбор строки «год | жанр | описание». Любая часть может быть '-'."""
    bits = (text or "").split("|", 2)
    year_raw = bits[0].strip() if bits else ""
    genre = bits[1].strip() if len(bits) > 1 else ""
    description = bits[2].strip() if len(bits) > 2 else ""

    def _empty(value: str) -> bool:
        return not value or value in {"-", "—", "–"}

    year: int | None
    if _empty(year_raw):
        year = None
    else:
        if not year_raw.isdigit() or not (1800 <= int(year_raw) <= 2100):
            raise ValueError("invalid year")
        year = int(year_raw)
    return {
        "year": year,
        "genre": None if _empty(genre) else genre,
        "description": None if _empty(description) else description,
    }


def parse_code(text: str | None) -> int | None:
    """Извлекает положительный целочисленный код из текста (« 012 » → 12)."""
    if text is None:
        return None
    raw = text.strip()
    if not raw.isdigit():
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < 1:
        return None
    return value


def parse_add_args(args: str | None) -> tuple[int | None, str | None]:
    """Разбор аргументов /add: (код или None, название или None).

    /add 12 Интерстеллар → (12, "Интерстеллар")
    /add 12 → (12, None)
    /add Интерстеллар → (None, "Интерстеллар")
    /add → (None, None)
    """
    raw = (args or "").strip()
    if not raw:
        return None, None
    first, _, rest = raw.partition(" ")
    code = parse_code(first)
    if code is not None:
        title = rest.strip() or None
        return code, title
    return None, raw

