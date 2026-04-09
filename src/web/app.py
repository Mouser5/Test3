import sys
import logging
import html
from pathlib import Path
import html

src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import streamlit as st
from sqlalchemy.orm import Session
from web.database import SessionLocal, init_db
from web.models import User
from web.schemas import UserCreate, UserLogin
from web.auth import register_user, authenticate_user, create_access_token
from web.bot_crud import (
    create_bot,
    get_user_bots,
    get_bot_by_id,
    delete_bot,
    save_game_result,
    get_user_game_history,
    get_bot_stats,
)
from web.agent_validator import AgentValidator
from web.game_runner import (
    run_single_game,
    BUILTIN_AGENTS,
    SingleGameResult,
    BenchmarkResult,
)
from web.schemas import UserCreate, UserLogin, BotCreate
from web.admin import ensure_default_admin_exists, get_users as _get_users, create_user_with_role as _create_user_with_role, set_user_role as _set_user_role, create_bot_for_user as _create_bot_for_user

st.set_page_config(
    page_title="Гномы-вредители: Дуэль",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

logger = logging.getLogger(__name__)
import html as _html

def render_scrollable_code(code: str, height: int = 360) -> str:
    esc = _html.escape(code)
    return (
        f"<div style=\"height:{height}px; overflow:auto; border:1px solid #ddd; border-radius:6px; "
        f"padding:6px; background:#f7f7f7; font-family:monospace; white-space:pre; font-size:12px;\">"
        f"<pre style=\"margin:0\">{esc}</pre>"
        "</div>"
    )

def render_scrollable_code(code: str, height: int = 360) -> str:
    # Minimal fallback: render as a plain pre block (no scroll wrapper)
    import html as _html
    esc = _html.escape(code)
    return f"<pre style='white-space:pre; font-family:monospace; font-size:12px'>{esc}</pre>" 

st.markdown(
    """
<style>
.stApp {
    max-width: 1400px;
}
.code-container {
    background-color: #1e1e1e;
    border-radius: 10px;
    padding: 15px;
    color: #d4d4d4;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
}
.success-box {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 5px;
    padding: 10px;
    color: #155724;
}
.error-box {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 5px;
    padding: 10px;
    color: #721c24;
}
.uml-container {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
}
.log-container {
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    font-family: monospace;
    font-size: 12px;
    max-height: 400px;
    overflow-y: auto;
}
</style>
""",
    unsafe_allow_html=True,
)


def init_database():
    try:
        init_db()
    except Exception as e:
        st.warning(f"БД недоступна: {e}")
    # Ensure a default admin exists
    try:
        from web.database import SessionLocal
        db = SessionLocal()
        try:
            ensure_default_admin_exists(db)
        finally:
            db.close()
    except Exception:
        pass

def admin_bootstrap():
    """Пытаемся автоматически создать админа в начале выполнения приложения."""
    try:
        from web.database import SessionLocal
        db = SessionLocal()
        try:
            ensure_default_admin_exists(db)
        finally:
            db.close()
        logger.info("Admin bootstrap executed at startup")
        print("Admin bootstrap executed at startup")
    except Exception as e:
        logger.debug(f"Admin bootstrap failed at startup: {e}", exc_info=True)
        print(f"Admin bootstrap failed at startup: {e}")

def get_db_session():
    if "db_session" not in st.session_state:
        db = SessionLocal()
        st.session_state.db_session = db
        try:
            ensure_default_admin_exists(db)
        except Exception:
            import traceback
            traceback.print_exc()
        return db
    return st.session_state.db_session


def init_auth_state():
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None


def login_user(db: Session, username: str, password: str):
    user, error = authenticate_user(db, UserLogin(username=username, password=password))
    if error:
        return False, error
    token = create_access_token(data={"sub": str(user.id), "username": user.username})
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.access_token = token
    # Refresh role from DB to ensure correct admin panel visibility after login
    try:
        fresh = db.query(User).filter(User.id == user.id).first()
        role = getattr(fresh, "role", "user") if fresh else getattr(user, "role", "user")
    except Exception:
        role = getattr(user, "role", "user")
    st.session_state.user_role = role
    return True, ""


def logout_user():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.access_token = None
    if "db_session" in st.session_state:
        st.session_state.db_session.close()
        del st.session_state.db_session


def show_login(db: Session):
    st.markdown("### 🔐 Вход в систему")

    with st.form("login_form"):
        username = st.text_input("Имя пользователя")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Войти", type="primary")

        if submit:
            if not username or not password:
                st.error("Заполните все поля")
            else:
                success, error = login_user(db, username, password)
                if success:
                    st.success("Вход выполнен!")
                    st.rerun()
                else:
                    st.error(error)

    st.markdown("---")
    st.markdown("### 📝 Регистрация")

    with st.form("register_form"):
        new_username = st.text_input("Новое имя пользователя")
        new_email = st.text_input("Email")
        new_password = st.text_input("Пароль", type="password")
        confirm_password = st.text_input("Подтвердите пароль", type="password")
        submit_reg = st.form_submit_button("Зарегистрироваться", type="primary")

        if submit_reg:
            if not new_username or not new_email or not new_password:
                st.error("Заполните все поля")
            elif new_password != confirm_password:
                st.error("Пароли не совпадают")
            else:
                user, error = register_user(
                    db,
                    UserCreate(
                        username=new_username, email=new_email, password=new_password
                    ),
                )
                if error:
                    st.error(error)
                else:
                    st.success("Регистрация успешна! Теперь войдите.")

    st.markdown("---")
    st.markdown("### 📋 Требования к роботу")
    st.markdown(AgentValidator.get_agent_requirements_text())


def show_dashboard(db: Session):
    user_id = st.session_state.user_id

    st.sidebar.markdown(f"### 👤 {st.session_state.username}")
    if st.sidebar.button("🚪 Выйти", use_container_width=True):
        logout_user()
        st.rerun()

    st.sidebar.markdown("---")

    # Admin tab insertion if admin
    is_admin = False
    try:
        is_admin = (st.session_state.get("user_role", "user") == "admin")
    except Exception:
        is_admin = False
    if is_admin:
        tabs = st.tabs(["🎮 Игра", "🤖 Мои боты", "Админ панель", "Пользователи", "📊 История", "❓ Правила"])
    else:
        tabs = st.tabs(["🎮 Игра", "🤖 Мои боты", "📊 История", "❓ Правила"])

    with tabs[0]:
        show_game_tab(db, user_id)

    with tabs[1]:
        show_bots_tab(db, user_id)
    if is_admin:
        with tabs[2]:
            show_admin_panel(db)
        with tabs[3]:
            show_users_panel(db)
        with tabs[4]:
            show_history_tab(db, user_id)
        with tabs[5]:
            show_requirements()
    else:
        with tabs[2]:
            show_history_tab(db, user_id)
        with tabs[3]:
            show_requirements()


def show_users_panel(db: 'Session'):
    # Admin-specific: view all users and their bots with full code and per-bot delete.
    from web.models import User, Bot
    st.markdown("---")
    st.markdown("### Пользователи и Боты")
    # Simple user selector
    users = db.query(User).order_by(User.id).all()
    if not users:
        st.info("Нет пользователей в системе")
        return

    user_map = {f"{u.id} - {u.username}": u.id for u in users}
    sel_label = st.selectbox("Пользователь", list(user_map.keys()))
    sel_user_id = user_map[sel_label]

    bots = db.query(Bot).filter(Bot.user_id == sel_user_id).order_by(Bot.created_at.desc()).all()
    if not bots:
        st.info("У этого пользователя нет ботов.")
        return
    for bot in bots:
        owner = db.query(User).filter(User.id == bot.user_id).first()
        owner_name = owner.username if owner else "Unknown"
        with st.expander(f"🤖 {bot.name} (ID: {bot.id}) | Владельец: {owner_name}"):
            statz = get_bot_stats(db, bot.id)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Всего игр", statz["total"])
            with col2:
                st.metric("Побед", statz["wins"])
            with col3:
                st.metric("Поражений", statz["losses"])
            with col4:
                st.metric("Win Rate", f"{statz['win_rate']:.1f}%")
            st.code(bot.code, language="python")
            if st.button(f"Удалить бота {bot.id}", key=f"del_bot_{bot.id}"):
                if db is not None and bot is not None:
                    if db.query(Bot).filter(Bot.id == bot.id).delete():
                        db.commit()
                        st.success("Бот удалён")
                        st.experimental_rerun()


def show_admin_panel(db: Session):
    st.markdown("---")
    st.markdown("### Админ панель")
    db_session = get_db_session()
    with st.form("admin_create_user"):
        st.markdown("#### Создать пользователя")
        new_username = st.text_input("Имя пользователя")
        new_email = st.text_input("Email")
        new_password = st.text_input("Пароль", type="password")
        new_role = st.selectbox("Роль", ["user", "admin"])
        submitted_user = st.form_submit_button("Создать пользователя")
        if submitted_user:
            if not new_username or not new_email or not new_password:
                st.warning("Заполните все поля")
            else:
                user, err = _create_user_with_role(
                    db_session, UserCreate(username=new_username, email=new_email, password=new_password), new_role
                )
                if err:
                    st.error(err)
                else:
                    st.success(f"Пользователь создан: {user.username} (id={user.id}, роль={user.role})")

    with st.form("admin_upload_bot"):
        st.markdown("#### Загружать бота для пользователя")
        users = _get_users(db_session)
        user_choices = {f"{u.id} - {u.username}": u.id for u in users}
        selected_user_label = st.selectbox("Пользователь:", list(user_choices.keys()))
        selected_user_id = user_choices[selected_user_label]
        bot_name = st.text_input("Имя бота")
        bot_code_text = st.text_area("Код бота (Python)", height=300, key="admin_code_text")
        bot_code_file = st.file_uploader("Или загрузите файл .py", type=["py"])
        submitted_bot = st.form_submit_button("Загрузить бота")

        code = None
        if bot_code_file is not None:
            file_bytes = bot_code_file.read()
            try:
                code = file_bytes.decode("utf-8")
            except Exception:
                code = file_bytes.decode(errors="ignore")
        elif bot_code_text:
            code = bot_code_text

        if submitted_bot:
            if not bot_name or not code:
                st.warning("Введите имя бота и код")
            else:
                bot_data = BotCreate(name=bot_name, code=code)
                bot = _create_bot_for_user(db_session, selected_user_id, bot_data)
                st.success(f"Бот '{bot.name}' загружен пользователю ID {selected_user_id}")

    with st.form("admin_set_role"):
        st.markdown("#### Назначить роль пользователю")
        users = _get_users(db_session)
        user_choices2 = {f"{u.id} - {u.username} (текущая роль: {u.role})": u.id for u in users}
        sel_user = st.selectbox("Пользователь:", list(user_choices2.keys()))
        sel_user_id = user_choices2[sel_user]
        new_role2 = st.selectbox("Новая роль", ["user", "admin"])
        submitted_role = st.form_submit_button("Назначить")
        if submitted_role:
            ok = _set_user_role(db_session, sel_user_id, new_role2)
            if ok:
                st.success(f"Пользователь {sel_user_id} получил роль {new_role2}")
            else:
                st.error("Не удалось обновить роль")

    # Админ-панель вынесена в отдельную вкладку через show_admin_panel

def show_game_tab(db: Session, user_id: int):
    from web.logger import (
        log_game_start,
        log_game_end,
        log_game_error,
        log_bot_load_for_game,
        log_bot_loaded,
    )
    import uuid

    st.markdown("### 🎮 Запуск игры")

    user_bots = get_user_bots(db, user_id)
    bot_options = {bot.id: bot.name for bot in user_bots}
    bot_options[-1] = "Нет бота (человек)"

    col1, col2 = st.columns(2)

    with col1:
        opponent = st.selectbox(
            "Противник:",
            options=list(BUILTIN_AGENTS.keys()),
            format_func=lambda x: {
                "random": "🎲 RandomAgent",
                "heuristic": "🧠 HeuristicAgent",
                "smart": "🤖 SmartAgent",
            }.get(x, x),
        )

    if user_bots:
        with col2:
            selected_bot = st.selectbox(
                "Ваш бот:",
                options=list(bot_options.keys()),
                format_func=lambda x: bot_options.get(x, "Выбрать бота"),
            )
    else:
        st.info("У вас нет ботов. Создайте бота на вкладке 'Мои боты'")
        return

    num_games = 1

    if st.button("🚀 Запустить игру", type="primary", use_container_width=True):
        if selected_bot == -1:
            st.warning("Выберите бота для игры")
            return

        bot = get_bot_by_id(db, selected_bot)
        if not bot:
            st.error("Бот не найден")
            return

        log_bot_load_for_game(bot.id, bot.name)

        import random
        import math

        module_name = f"bot_{bot.id}"
        try:
            exec_globals = {
                "__name__": module_name,
                "random": random,
                "math": math,
            }
            exec(compile(bot.code, f"<bot_{bot.id}>", "exec"), exec_globals)

            agent_class = None
            for name in exec_globals:
                obj = exec_globals[name]
                if isinstance(obj, type) and hasattr(obj, "choose_action"):
                    agent_class = obj
                    break

            if agent_class is None:
                log_bot_loaded(bot.id, bot.name, False)
                st.error("Не найден класс агента с методом choose_action")
                return

            log_bot_loaded(bot.id, bot.name, True)
        except SyntaxError as e:
            log_bot_loaded(bot.id, bot.name, False)
            st.error(f"Синтаксическая ошибка (строка {e.lineno}): {e.msg}")
            return
        except Exception as e:
            log_bot_loaded(bot.id, bot.name, False)
            st.error(f"Ошибка при загрузке: {str(e)}")
            return

        progress_bar = st.progress(0, text="Подготовка...")
        progress_bar.progress(25, text="Запуск игры...")

        game_id = str(uuid.uuid4())[:8]
        log_game_start(game_id, bot.name, opponent.capitalize())

        try:
            opponent_class = BUILTIN_AGENTS[opponent]
            result = run_single_game(
                agent_class,
                opponent_class,
                agent1_name=bot.name,
                agent2_name=opponent.capitalize(),
            )

            winner_name = result.winner_name if result.winner is not None else "Ничья"
            log_game_end(game_id, winner_name, result.total_scores, result.turns)
            progress_bar.progress(100, text="Готово!")

        except Exception as e:
            log_game_error(game_id, str(e))
            progress_bar.progress(100, text="Ошибка!")
            raise

        from web.schemas import GameResultCreate

        result_data = GameResultCreate(
            bot_id=bot.id,
            opponent_type=opponent,
            opponent_id=None,
            result="win"
            if result.winner == 0
            else ("loss" if result.winner == 1 else "draw"),
            user_score=result.total_scores.get(0, 0),
            opponent_score=result.total_scores.get(1, 0),
            turns=result.turns,
        )
        save_game_result(db, user_id, result_data)

        show_single_game_result(result)


def show_bots_tab(db: Session, user_id: int):
    from web.logger import log_bot_upload
    # Admin should see all bots across users
    try:
        is_admin_view = st.session_state.get("user_role", "user") == "admin"
    except Exception:
        is_admin_view = False

    st.markdown("### 🤖 Мои боты" if not is_admin_view else "### ВСЕ БОТЫ")

    with st.expander("➕ Загрузить нового бота", expanded=False):
        with st.form("upload_bot"):
            bot_name = st.text_input("Название бота", placeholder="MySuperBot")
            bot_code_text = st.text_area("Код бота (Python)", height=300, key="code_text")
            bot_code_file = st.file_uploader("Или загрузите файл .py", type=["py"])
            submit = st.form_submit_button("Загрузить", type="primary")

            code = None
            if bot_code_file is not None:
                file_bytes = bot_code_file.read()
                try:
                    code = file_bytes.decode("utf-8")
                except Exception:
                    code = file_bytes.decode(errors="ignore")
            elif bot_code_text:
                code = bot_code_text

            if submit:
                if not bot_name or not code:
                    st.error("Заполните все поля")
                else:
                    validation = AgentValidator.validate_agent_class_from_code(code)
                    if validation.is_valid:
                        from web.schemas import BotCreate

                        bot_data = BotCreate(name=bot_name, code=code)
                        bot = create_bot(db, user_id, bot_data)
                        log_bot_upload(user_id, bot.name, bot.id)
                        st.success(f"Бот '{bot.name}' загружен!")
                        st.rerun()
                    else:
                        for error in validation.errors:
                            st.error(error)

    st.markdown("---")
    st.markdown("#### 📂 Загруженные боты")

    # Admin sees all bots, regular users see only their bots
    if is_admin_view:
        from web.models import Bot as BotModel
        bots = db.query(BotModel).all()
    else:
        bots = get_user_bots(db, user_id)
    if not bots:
        st.info("У вас пока нет ботов. Загрузите первого бота!")
        return

    for bot in bots:
        bot_display_name = getattr(bot, 'name', 'BOT')
        bot_display_id = getattr(bot, 'id', '?')
        # Show owner for admin view
        try:
            from web.models import User
            owner = db.query(User).filter(User.id == bot.user_id).first()
            owner_name = owner.username if owner else "Unknown"
        except Exception:
            owner_name = "Unknown"
        title = f"🤖 {bot_display_name} (ID: {bot_display_id})"
        try:
            is_admin_view_local = (is_admin_view)
        except Exception:
            is_admin_view_local = False
        if is_admin_view_local:
            title += f" | Владельец: {owner_name}"
        with st.expander(title):
            stats = get_bot_stats(db, bot.id)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Всего игр", stats["total"])
            with col2:
                st.metric("Побед", stats["wins"])
            with col3:
                st.metric("Поражений", stats["losses"])
            with col4:
                st.metric("Win Rate", f"{stats['win_rate']:.1f}%")
            # Show as standard code block (no extra wrappers)
            st.code(bot.code, language="python")

            # Delete button: admins can delete any bot by its owner, regular users only their own
            if st.button("🗑️ Удалить", key=f"delete_{bot.id}"):
                if is_admin_view:
                    owner_id = bot.user_id
                else:
                    owner_id = user_id
                if delete_bot(db, bot.id, owner_id):
                    st.success("Бот удалён")
                    st.rerun()

            # (Удаление для администратора обрабатывается в верхнем блоке, чтобы избежать дублирования)


def show_history_tab(db: Session, user_id: int):
    st.markdown("### 📊 История игр")

    history = get_user_game_history(db, user_id)

    if not history:
        st.info("У вас пока нет сыгранных игр")
        return

    for game in history:
        with st.expander(f"Игра #{game.id} - {game.opponent_type} | {game.result}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Ваш счёт", game.user_score)
            with col2:
                st.metric("Счёт противника", game.opponent_score)
            with col3:
                st.metric("Ходов", game.turns)
            st.caption(f"Дата: {game.played_at}")


def show_requirements():
    st.markdown(AgentValidator.get_agent_requirements_text())

    st.markdown("### 📊 UML-диаграмма интерфейса агента")

    uml_code = """
@startuml
skinparam classAttributeIconSize 0
skinparam monochrome true

interface "<<interface>>\\nAgentInterface" as IAgent {
    + player_id: int
    + choose_action(game: Game): Optional[AgentAction]
}

class RandomAgent {
    - player_id: int
    + choose_action(game: Game): Optional[AgentAction]
}

class HeuristicAgent {
    - player_id: int
    - logger: Logger
    + choose_action(game: Game): Optional[AgentAction]
    - _select_best_action(game, actions): AgentAction
    - _choose_best_build_action(game, actions): ActionBuild
}

class "Ваш робот" as UserAgent <<custom>> {
    - player_id: int
    + choose_action(game: Game): Optional[AgentAction]
}

IAgent <|.. RandomAgent
IAgent <|.. HeuristicAgent
IAgent <|.. UserAgent

note right of UserAgent
  Вы должны реализовать
  класс с таким интерфейсом
end note

@enduml
"""

    st.code(uml_code, language="plantuml", line_numbers=False)
    st.info("Визуализировать: https://www.plantuml.com/plantuml/uml/")


def show_single_game_result(result: SingleGameResult):
    if result.errors:
        st.error("❌ Игра завершена с ошибкой!")
        for error in result.errors:
            with st.expander("🔴 Показать ошибку"):
                st.code(error, language="text")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        if result.winner == 0:
            st.success(f"🏆 Победитель: **{result.winner_name}**")
        elif result.winner == 1:
            st.error(f"Победитель: **{result.winner_name}**")
        else:
            st.info("🤝 Ничья!")

    with col2:
        st.metric("Ваш робот", f"{result.total_scores[0]} очков")

    with col3:
        st.metric("Противник", f"{result.total_scores[1]} очков")

    st.metric("Всего ходов", result.turns)

    st.markdown("#### 📜 Лог игры")

    log_text = ""
    for log in result.logs:
        player_marker = "👤 ВЫ" if log.player_id == 0 else "🤖 ОПП"
        gold_str = f" ✨ ЗОЛОТО: {log.gold_found}!" if log.gold_found else ""
        log_text += f"Ход {log.turn_number} (Раунд {log.round_number}) [{player_marker}]: {log.action_description}{gold_str}\n"

    with st.expander("Показать полный лог"):
        st.code(log_text, language="text")


def show_benchmark_result(result: BenchmarkResult):
    st.markdown("#### 📊 Статистика бенчмарка")

    col1, col2, col3 = st.columns(3)

    with col1:
        wins_user = sum(v for k, v in result.wins.items() if k != "draw")
        pct = 100 * wins_user / result.total_games if result.total_games > 0 else 0
        st.metric("Побед", f"{wins_user} ({pct:.1f}%)")

    with col2:
        draws = result.wins.get("draw", 0)
        pct_draw = 100 * draws / result.total_games if result.total_games > 0 else 0
        st.metric("Ничьих", f"{draws} ({pct_draw:.1f}%)")

    with col3:
        st.metric("Всего игр", result.total_games)

    col4, col5 = st.columns(2)

    with col4:
        st.metric("Всего ходов", result.total_turns)

    with col5:
        st.metric("Время", f"{result.elapsed_time:.2f} сек")

    if result.total_errors > 0:
        st.warning(f"⚠️ Ошибок: {result.total_errors}")


def main():
    init_database()
    init_auth_state()

    admin_bootstrap()
    st.title("⛏️ Гномы-вредители: Дуэль")
    st.markdown("##### Карточная игра для обучения ИИ-агентов")

    db = get_db_session()

    if st.session_state.user_id is None:
        show_login(db)
    else:
        show_dashboard(db)


if __name__ == "__main__":
    main()
# render_scrollable_code removed: revert to standard code display
