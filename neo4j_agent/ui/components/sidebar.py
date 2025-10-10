"""Sidebar component for Neo4j Text2Cypher agent.

Displays:
- Example questions from config
- Reset chat button
- System information (LLM config, Neo4j database)
"""

from typing import Callable

from langchain_neo4j import Neo4jGraph
from nicegui import ui

from neo4j_agent.utils.config import AppSettings


def create_sidebar(
    settings: AppSettings,
    graph: Neo4jGraph,
    on_example_click: Callable[[str], None],
    on_reset_click: Callable[[], None]
):
    """Create sidebar with example questions and system info.

    Args:
        settings: Application settings
        graph: Neo4j graph connection
        on_example_click: Callback when example question is clicked, receives question text
        on_reset_click: Callback when reset button is clicked
    """
    with ui.column().classes('p-4 themed-element overflow-y-auto').style(
        'width: 320px; '
        'background: var(--neo4j-bg-secondary); '
        'color: var(--neo4j-text-primary); '
        'border-right: 1px solid var(--neo4j-border);'
    ):
        # Example Questions section
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('lightbulb', size='sm').style('color: #FFC450')  # Yellow
            ui.label('Example Questions').classes('text-lg font-bold').style('color: var(--neo4j-text-primary)')

        # Example questions from config
        for question in settings.ui.example_questions:
            display_text = question[:60] + '...' if len(question) > 60 else question

            ui.button(
                display_text,
                on_click=lambda q=question: on_example_click(q)
            ).props('flat align=left').classes('w-full text-left mb-2 normal-case example-question-btn').style(
                'text-transform: none; '
                'justify-content: flex-start; '
                'border: 1px solid var(--neo4j-border); '
                'border-radius: 6px; '
                'padding: 12px;'
            )

        # Reset Chat button (centered, smaller than questions, solid like Send button)
        with ui.row().classes('w-full justify-center mt-3'):
            ui.button(
                'RESET CHAT',
                icon='refresh',
                on_click=on_reset_click
            ).props('dense').style(
                'background: #014063 !important; '
                'color: white !important; '
                'border-radius: 6px;'
            )

        ui.separator().classes('my-4').style('background: var(--neo4j-border)')

        # System Information section
        with ui.row().classes('items-center gap-2 mb-2'):
            ui.icon('settings', size='sm').style('color: #999999')  # Gray
            ui.label('System Information').classes('text-lg font-bold').style('color: var(--neo4j-text-primary)')

        # LLM Configuration subsection (key-value grid layout)
        ui.label('LLM Configuration').classes('text-base font-semibold ml-6 mb-1').style('color: var(--neo4j-text-primary)')

        with ui.grid(columns=2).classes('ml-8 gap-x-4 gap-y-1 text-sm'):
            # Provider row
            ui.label('Provider').classes('font-semibold').style('color: var(--neo4j-text-primary)')
            ui.label(settings.llm.provider).style('color: var(--neo4j-text-secondary)')

            # Model row
            ui.label('Model').classes('font-semibold').style('color: var(--neo4j-text-primary)')
            ui.label(settings.llm.model).style('color: var(--neo4j-text-secondary)')

            # Temperature row
            ui.label('Temperature').classes('font-semibold').style('color: var(--neo4j-text-primary)')
            ui.label(str(settings.llm.temperature)).style('color: var(--neo4j-text-secondary)')

        ui.separator().classes('my-3').style('background: var(--neo4j-border)')

        # Neo4j Database subsection (key-value grid layout)
        ui.label('Neo4j Database').classes('text-base font-semibold ml-6 mb-1').style('color: var(--neo4j-text-primary)')

        # Get Neo4j version dynamically
        try:
            result = graph.query("CALL dbms.components() YIELD name, versions RETURN versions[0] as version")
            neo4j_version = result[0]['version'] if result else 'Unknown'
        except Exception:
            neo4j_version = 'Unknown'

        with ui.grid(columns=2).classes('ml-8 gap-x-4 gap-y-1 text-sm'):
            # Version row
            ui.label('Version').classes('font-semibold').style('color: var(--neo4j-text-primary)')
            ui.label(neo4j_version).style('color: var(--neo4j-text-secondary)')

            # Database row
            ui.label('Database').classes('font-semibold').style('color: var(--neo4j-text-primary)')
            ui.label(settings.neo4j.database).style('color: var(--neo4j-text-secondary)')

            # Status row
            ui.label('Status').classes('font-semibold').style('color: var(--neo4j-text-primary)')
            with ui.row().classes('items-center gap-1'):
                ui.icon('check_circle', size='xs').style('color: #3F7824')
                ui.label('Connected').style('color: #3F7824')
