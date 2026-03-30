import sys
from pathlib import Path

src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import streamlit as st
from sqlalchemy.orm import Session
from web.database import SessionLocal, init_db
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

st.set_page_config(
    page_title="Гномы-вредители: Дуэль",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

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


def get_db_session():
    if "db_session" not in st.session_state:
        st.session_state.db_session = SessionLocal()
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

    tabs = st.tabs(["🎮 Игра", "🤖 Мои боты", "📊 История", "❓ Правила"])

    with tabs[0]:
        show_game_tab(db, user_id)

    with tabs[1]:
        show_bots_tab(db, user_id)

    with tabs[2]:
        show_history_tab(db, user_id)

    with tabs[3]:
        show_requirements()


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

    st.markdown("### 🤖 Мои боты")

    with st.expander("➕ Загрузить нового бота", expanded=False):
        with st.form("upload_bot"):
            bot_name = st.text_input("Название бота", placeholder="MySuperBot")
            bot_code = st.text_area("Код бота (Python)", height=300)
            submit = st.form_submit_button("Загрузить", type="primary")

            if submit:
                if not bot_name or not bot_code:
                    st.error("Заполните все поля")
                else:
                    validation = AgentValidator.validate_agent_class_from_code(bot_code)
                    if validation.is_valid:
                        from web.schemas import BotCreate

                        bot_data = BotCreate(name=bot_name, code=bot_code)
                        bot = create_bot(db, user_id, bot_data)
                        log_bot_upload(user_id, bot.name, bot.id)
                        st.success(f"Бот '{bot.name}' загружен!")
                        st.rerun()
                    else:
                        for error in validation.errors:
                            st.error(error)

    st.markdown("---")
    st.markdown("#### 📂 Загруженные боты")

    bots = get_user_bots(db, user_id)

    if not bots:
        st.info("У вас пока нет ботов. Загрузите первого бота!")
        return

    for bot in bots:
        with st.expander(f"🤖 {bot.name} (ID: {bot.id})"):
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

            st.code(
                bot.code[:500] + "..." if len(bot.code) > 500 else bot.code,
                language="python",
            )

            if st.button("🗑️ Удалить", key=f"delete_{bot.id}"):
                if delete_bot(db, bot.id, user_id):
                    st.success("Бот удалён")
                    st.rerun()


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

    st.title("⛏️ Гномы-вредители: Дуэль")
    st.markdown("##### Карточная игра для обучения ИИ-агентов")

    db = get_db_session()

    if st.session_state.user_id is None:
        show_login(db)
    else:
        show_dashboard(db)


if __name__ == "__main__":
    main()
