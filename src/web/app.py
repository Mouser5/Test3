import sys
from pathlib import Path

src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import streamlit as st
from session_manager import session_manager
from agent_validator import AgentValidator
from game_runner import (
    run_single_game,
    run_benchmark,
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


def init_session():
    if "session_id" not in st.session_state:
        st.session_state.session_id = session_manager.create_session()
    if "agent_loaded" not in st.session_state:
        st.session_state.agent_loaded = False
    if "agent_class" not in st.session_state:
        st.session_state.agent_class = None
    if "uploaded_code" not in st.session_state:
        st.session_state.uploaded_code = None


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

    st.info("""
    💡 **Совет**: Используйте PlantUML-сервер или плагин IDE для визуализации диаграммы.
    
    Онлайн-визуализатор: https://www.plantuml.com/plantuml/uml/
    """)


def show_upload_section():
    st.markdown("### 📤 Загрузка робота")

    uploaded_file = st.file_uploader(
        "Выберите файл .py с кодом вашего робота",
        type=["py"],
        help="Файл должен содержать класс с методом choose_action(game)",
    )

    if uploaded_file is not None:
        code = uploaded_file.read().decode("utf-8")
        st.session_state.uploaded_code = code

        st.markdown("**Предпросмотр кода:**")
        st.code(code, language="python", line_numbers=True)

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("✅ Проверить и загрузить", type="primary"):
                agent_class, errors = session_manager.load_agent_from_code(
                    st.session_state.session_id, code
                )

                if agent_class is not None:
                    validation = AgentValidator.validate_agent_class(agent_class)

                    if validation.is_valid:
                        st.session_state.agent_class = agent_class
                        st.session_state.agent_loaded = True

                        st.markdown(
                            """
                        <div class="success-box">
                            ✅ <strong>Робот успешно загружен!</strong><br>
                            Класс: {} <br>
                            Готов к запуску игры.
                        </div>
                        """.format(validation.class_name),
                            unsafe_allow_html=True,
                        )

                        if validation.warnings:
                            for warning in validation.warnings:
                                st.warning(warning)
                    else:
                        for error in validation.errors:
                            st.error(f"❌ {error}")
                else:
                    for error in errors:
                        st.error(f"❌ {error}")

        with col2:
            if st.button("🗑️ Очистить"):
                st.session_state.agent_loaded = False
                st.session_state.agent_class = None
                st.session_state.uploaded_code = None
                st.rerun()

    if st.session_state.agent_loaded:
        st.success("✅ Робот загружен и готов к игре")


def show_game_section():
    st.markdown("---")
    st.markdown("### 🎮 Запуск игры")

    if not st.session_state.agent_loaded:
        st.warning("⚠️ Сначала загрузите робота во вкладке 'Загрузка робота'")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        game_mode = st.radio(
            "Режим игры:",
            options=["single", "benchmark"],
            format_func=lambda x: (
                "🎯 Одна подробная игра" if x == "single" else "📊 Много игр (бенчмарк)"
            ),
            horizontal=True,
        )

    with col2:
        opponent = st.selectbox(
            "Выберите противника:",
            options=list(BUILTIN_AGENTS.keys()),
            format_func=lambda x: {
                "random": "🎲 RandomAgent (случайный)",
                "heuristic": "🧠 HeuristicAgent (умный)",
                "smart": "🤖 SmartAgent (продвинутый)",
            }.get(x, x),
        )

    if game_mode == "benchmark":
        num_games = st.slider(
            "Количество игр:", min_value=10, max_value=1000, value=100, step=10
        )
    else:
        num_games = 1

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    with col_btn1:
        run_button = st.button("🚀 Запустить игру", type="primary")

    with col_btn2:
        if st.button("🔄 Сбросить результаты"):
            if "last_result" in st.session_state:
                del st.session_state.last_result
            st.rerun()

    if run_button:
        agent_class = st.session_state.agent_class
        opponent_class = BUILTIN_AGENTS[opponent]

        progress_text = (
            "Выполняется игра..."
            if game_mode == "single"
            else f"Выполняется {num_games} игр..."
        )
        progress_bar = st.progress(0, text=progress_text)

        if game_mode == "single":
            result = run_single_game(
                agent_class,
                opponent_class,
                agent1_name="Ваш робот",
                agent2_name=opponent.capitalize(),
            )
            st.session_state.last_result = ("single", result)
            progress_bar.progress(100, text="Игра завершена!")
        else:
            progress_bar.progress(50, text="Выполнение бенчмарка...")
            result = run_benchmark(
                agent_class,
                opponent_class,
                num_games,
                agent1_name="Ваш робот",
                agent2_name=opponent.capitalize(),
            )
            st.session_state.last_result = ("benchmark", result)
            progress_bar.progress(100, text="Бенчмарк завершён!")

    if "last_result" in st.session_state:
        mode, result = st.session_state.last_result

        st.markdown("---")
        st.markdown("### 📋 Результаты")

        if mode == "single":
            show_single_game_result(result)
        else:
            show_benchmark_result(result)


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
        wins_user = result.wins.get("Ваш робот", 0)
        pct = 100 * wins_user / result.total_games if result.total_games > 0 else 0
        st.metric("Побед вашего робота", f"{wins_user} ({pct:.1f}%)")

    with col2:
        wins_opp = (
            result.wins.get(list(result.wins.keys())[1], 0)
            if len(result.wins) > 1
            else 0
        )
        for key in result.wins:
            if key not in ["Ваш робот", "draw"]:
                wins_opp = result.wins[key]
                break
        pct_opp = 100 * wins_opp / result.total_games if result.total_games > 0 else 0
        st.metric("Побед противника", f"{wins_opp} ({pct_opp:.1f}%)")

    with col3:
        draws = result.wins.get("draw", 0)
        pct_draw = 100 * draws / result.total_games if result.total_games > 0 else 0
        st.metric("Ничьих", f"{draws} ({pct_draw:.1f}%)")

    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric("Всего игр", result.total_games)

    with col5:
        st.metric("Всего ходов", result.total_turns)

    with col6:
        st.metric("Игр/сек", f"{result.games_per_second:.1f}")

    if result.total_errors > 0:
        st.warning(f"⚠️ Обнаружено {result.total_errors} ошибок при выполнении")

    st.metric("Время выполнения", f"{result.elapsed_time:.2f} сек")


def main():
    init_session()

    st.title("⛏️ Гномы-вредители: Дуэль")
    st.markdown("##### Карточная игра для обучения ИИ-агентов")

    st.markdown("""
    Добро пожаловать в систему тестирования роботов для игры **"Гномы-вредители: Дуэль"**!
    
    **Как пользоваться:**
    1. 📖 Изучите требования к роботу во вкладке **"Правила и UML"**
    2. 📤 Загрузите свой код во вкладке **"Загрузка робота"**
    3. 🎮 Запустите игру и анализируйте результаты
    """)

    tab1, tab2, tab3 = st.tabs(["📖 Правила и UML", "📤 Загрузка робота", "🎮 Игра"])

    with tab1:
        show_requirements()

    with tab2:
        show_upload_section()

    with tab3:
        show_game_section()

    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #666; font-size: 12px;">
        Гномы-вредители: Дуэль — Система тестирования роботов | Session ID: {}
    </div>
    """.format(st.session_state.session_id),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
