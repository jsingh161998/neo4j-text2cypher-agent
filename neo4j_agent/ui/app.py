"""NiceGUI web application for Neo4j Text2Cypher agent.

This module provides a modern web interface using NiceGUI 3.0 with custom Neo4j-inspired theme.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from nicegui import app, ui

from neo4j_agent.agent import create_text2cypher_workflow
from neo4j_agent.ui.components.chat import create_chat_area
from neo4j_agent.ui.components.settings import create_settings_modal
from neo4j_agent.ui.components.sidebar import create_sidebar
from neo4j_agent.ui.session import SessionManager, cleanup_inactive_sessions
from neo4j_agent.ui.theme import ThemeToggle, setup_neo4j_theme
from neo4j_agent.utils.config import AppSettings
from neo4j_agent.utils.llm import create_llm
from neo4j_agent.utils.neo4j import create_neo4j_graph
from neo4j_agent.utils.schema import get_schema

# Load environment variables from .env file
load_dotenv()

# Global app state (initialized once at startup)
settings: AppSettings | None = None
workflow = None
graph = None


def initialize_app():
    """Initialize application components once at startup."""
    global settings, workflow, graph

    print("Initializing IQS Data Explorer...")

    # Load configuration
    config_path = Path(__file__).parent.parent.parent / 'app-config' / 'config.yml'
    settings = AppSettings.from_yaml(config_path)
    print("✅ Configuration loaded")

    # Connect to Neo4j
    graph = create_neo4j_graph(settings.neo4j)
    print("✅ Neo4j connected")

    # Load database schema
    schema = get_schema(graph, cache_path=settings.neo4j.schema_cache_path)
    print("✅ Schema loaded")

    # Initialize LLM
    llm = create_llm(settings.llm)
    print("✅ LLM initialized")

    # Create workflow
    workflow = create_text2cypher_workflow(settings)
    print("✅ Workflow created")

    # Start background cleanup task
    asyncio.create_task(cleanup_inactive_sessions(settings))
    print("✅ Session cleanup task started")

    print("🚀 Application ready!")


# Initialize app components at startup (before any requests)
app.on_startup(initialize_app)


@ui.page('/')
def index():
    """Main page with Text2Cypher chat interface.

    Provides a full-featured chat interface for natural language to Cypher queries,
    with real-time workflow execution, results visualization, and session management.
    """

    # Set up custom Neo4j theme
    setup_neo4j_theme()

    # Initialize session and theme management
    session = SessionManager()
    theme_toggle = ThemeToggle()

    # Header with Neo4j branding
    with ui.header().style('background: #014063 !important'):
        with ui.row().classes('w-full items-center justify-between px-4'):
            ui.label(settings.ui.title).classes('text-h4 text-white font-semibold')
            with ui.row().classes('gap-2 items-center'):
                # Theme toggle
                theme_toggle.create_toggle_button()

                # Settings button (per-session, no YAML writes)
                open_settings_dialog = create_settings_modal(settings=settings)
                ui.button(
                    icon='tune',
                    on_click=open_settings_dialog
                ).props('flat round').style('color: white !important').tooltip('Query Settings')

    # Configure full-height layout (NiceGUI best practice for header + content)
    ui.context.client.page_container.default_slot.children[0].props(':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"')
    ui.context.client.content.classes('h-full')

    # Main layout: Sidebar (left) + Chat area (right)
    # Callback references for sidebar interactions
    clear_chat_ui = None
    submit_question_ref = None

    def handle_example_click(question: str):
        """Submit example question to workflow."""
        if submit_question_ref:
            submit_question_ref(question)

    def handle_reset_chat():
        """Reset chat conversation and UI."""
        if clear_chat_ui:
            session.reset_chat(workflow=workflow, clear_ui_callback=clear_chat_ui)

    with ui.row().classes('w-full h-full items-stretch'):
        # Sidebar - example questions and system info
        create_sidebar(
            settings=settings,
            graph=graph,
            on_example_click=handle_example_click,
            on_reset_click=handle_reset_chat
        )

        # Chat area - conversation interface with workflow execution
        clear_chat_ui, submit_question_ref = create_chat_area(
            settings=settings,
            session=session,
            workflow=workflow
        )


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='IQS Data Explorer',
        port=8080,
        reload=True,
        show=True,  # Auto-open browser on startup
    )
