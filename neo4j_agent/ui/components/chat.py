"""Chat component for Neo4j Text2Cypher agent.

Displays:
- Scope description (if configured)
- Scrollable chat messages container with auto-scroll
- Input field with send button (fixed at bottom)
- Workflow streaming with real-time step indicators
- Bot responses with answer, details, and execution sections
"""

import asyncio
from typing import Callable

import pandas as pd
from nicegui import ui

from neo4j_agent.ui.components.execution_summary import render_execution_summary
from neo4j_agent.ui.session import SessionManager
from neo4j_agent.ui.streaming import WorkflowStreamer
from neo4j_agent.utils.config import AppSettings


def create_chat_area(
    settings: AppSettings,
    session: SessionManager,
    workflow
) -> tuple[Callable[[], None], Callable[[str], None]]:
    """Create chat area with messages and input field.

    Args:
        settings: Application settings
        session: Session manager for activity tracking
        workflow: LangGraph workflow for Text2Cypher execution

    Returns:
        Tuple of (clear_chat_ui, submit_question) callbacks for UI integration
    """
    # Main chat area (80% width) - constrained height, messages scroll, input stays at bottom
    with ui.column().classes('flex-1 themed-element').style(
        'background: var(--neo4j-bg-primary); '
        'color: var(--neo4j-text-primary); '
        'max-height: 100%; '  # Critical: respect flex-1 height allocation
        'overflow: hidden; '  # Prevent column from growing beyond allocation
        'display: flex; '
        'flex-direction: column;'
    ):
        # Scope description - fixed at top
        if settings.ui.scope_description:
            ui.label(settings.ui.scope_description).classes('text-base mb-4 px-4 pt-4').style(
                'color: var(--neo4j-text-secondary)'
            )

        # Chat messages container - scrollable area with auto-scroll support
        with ui.scroll_area().classes('w-full flex-1') as scroll_area:
            chat_container = ui.column().classes('w-full gap-4 px-4')

        async def _submit_question_async(question: str, session_settings: dict):
            """Async handler for question submission (runs in background task).

            Args:
                question: User's question
                session_settings: Pre-fetched session settings (captured from UI context)
            """
            # Disable input during processing
            input_field.enabled = False
            send_button.enabled = False

            # Clear input first
            input_field.value = ''

            # Display user question in chat
            with chat_container:
                with ui.card().classes('w-full user-question-card').style(
                    'background: var(--neo4j-bg-secondary); '
                    'border-left: 4px solid #0A6190; '
                    'margin-bottom: 1rem;'
                ):
                    ui.label('👤 You').classes('text-sm font-semibold mb-2').style(
                        'color: var(--neo4j-text-secondary);'
                    )
                    ui.markdown(question).classes('text-base').style(
                        'color: var(--neo4j-text-primary); '
                        'margin-left: 16px; '
                        'margin-right: 16px;'
                    )

            # Create assistant response card with workflow execution
            with chat_container:
                with ui.card().classes('w-full assistant-response-card').style(
                    'background: var(--neo4j-bg-primary); '
                    'border-left: 4px solid #00C48C; '
                    'margin-bottom: 1.5rem;'
                ):
                    ui.label('🤖 Assistant').classes('text-sm font-semibold').style(
                        'color: var(--neo4j-text-secondary); margin-bottom: 4px;'
                    )

                    # Initialize streaming UI components (always show status bar with spinner)
                    with ui.row().classes('items-center gap-2').style('margin-bottom: 4px; margin-left: 16px; margin-right: 16px;') as status_container:
                        status_spinner = ui.spinner(size='sm').style('color: var(--neo4j-text-secondary);')
                        status_bar = ui.label('Starting...').classes('text-sm').style(
                            'color: var(--neo4j-text-secondary); font-weight: 500;'
                        )

                    # Main content container for workflow output
                    content_container = ui.column().classes('w-full').style('gap: 4px;')

                    # Auto-scroll to show the new question and assistant card
                    await asyncio.sleep(0.1)  # Small delay to ensure rendering
                    scroll_area.scroll_to(percent=1e6)

                    try:
                        # Execute workflow with streaming
                        initial_state = {
                            "question": question,
                            "retry_count": 0,
                        }
                        # Pass session_settings to avoid accessing app.storage.client in background task
                        config = session.get_config(session_settings=session_settings)

                        # Stream workflow execution with visual progress
                        streamer = WorkflowStreamer(workflow)
                        final_state = await streamer.stream_workflow(
                            initial_state,
                            config,
                            progress_bar=status_bar,
                            progress_spinner=status_spinner,
                            steps_container=None
                        )

                        # Display final answer and details
                        with content_container:
                            render_response(final_state)

                        # Auto-scroll to show complete response
                        scroll_area.scroll_to(percent=1e6)

                    except Exception as e:
                        # Handle unexpected errors
                        content_container.clear()
                        with content_container:
                            ui.markdown(f"❌ **Unexpected Error**").classes('font-bold mb-2').style(
                                'color: #E74C3C;'
                            )
                            ui.code(str(e), language='text').classes('text-sm')

            # Re-enable input
            input_field.enabled = True
            send_button.enabled = True

        def submit_question(question: str):
            """Synchronous wrapper that captures session settings before calling async handler.

            This function runs in UI context and can access app.storage.client.
            It captures session settings, then passes them to the async function.

            Args:
                question: User's question
            """
            if not question.strip():
                return

            # Update activity (with session expiry check)
            if not session.update_activity():
                return  # Session expired

            # Capture session settings in UI context (MUST be done here, not in async function)
            from nicegui import app
            session_settings = app.storage.client.get('query_settings', {})

            # Launch async task with captured settings
            asyncio.create_task(_submit_question_async(question, session_settings))

        def render_response(final_state: dict):
            """Render workflow response with answer, query details, and execution info.

            Order:
            - ERROR: Error message → Cypher → Execution Summary (expanded)
            - SUCCESS: Execution Summary (collapsed) → Answer → Answer Details
            """
            has_error = final_state.get('error') is not None

            # ========================================
            # ERROR PATH
            # ========================================
            if has_error:
                # 1. Error message (prominent)
                ui.markdown(f"❌ **Error:** {final_state['error']}").classes('mb-2').style(
                    'color: #E74C3C;'
                )

                # 2. Show the problematic Cypher query
                cypher = final_state.get('cypher_query')
                if cypher:
                    ui.label('🔧 Generated Cypher Query').classes('text-sm font-semibold mb-2')
                    ui.code(cypher, language='cypher').classes('text-sm mb-4 cypher-code-block')

                # 3. Execution Summary (AUTO-EXPANDED on error)
                render_execution_summary(final_state, is_error=True)
                return  # Don't show answer/results sections

            # ========================================
            # SUCCESS PATH
            # ========================================

            # 1. Execution Summary FIRST (collapsed by default)
            render_execution_summary(final_state, is_error=False)

            # 2. Answer section (expanded)
            answer = final_state.get('final_answer', 'No answer generated')
            with ui.expansion('💬 Answer', value=True).props('dense').classes('w-full mb-2'):
                ui.markdown(answer).classes('text-base').style('color: var(--neo4j-text-primary);')

            # 3. Answer Details (collapsed) - Cypher + results table
            cypher = final_state.get('cypher_query')
            results = final_state.get('query_results')

            if cypher or results:
                with ui.expansion('📊 Answer Details').props('dense').classes('w-full mb-2'):
                    # Display generated Cypher query
                    if cypher:
                        ui.label('Generated Cypher Query:').classes('text-sm font-semibold mb-2')
                        ui.code(cypher, language='cypher').classes('text-sm mb-4 cypher-code-block')

                    # Display query results in table
                    if results and len(results) > 0:
                        # Create DataFrame and filter out unhashable columns (dicts, lists with dicts)
                        df = pd.DataFrame(results)

                        # Remove columns that contain dict/complex objects (can't display in table)
                        # These will be handled by the visualization component later
                        cols_to_keep = []
                        for col in df.columns:
                            # Check if column contains only hashable/primitive values
                            if df[col].apply(lambda x: isinstance(x, (str, int, float, bool, type(None)))).all():
                                cols_to_keep.append(col)

                        df = df[cols_to_keep] if cols_to_keep else df

                        # Deduplicate if possible
                        try:
                            df = df.drop_duplicates()
                        except TypeError:
                            # Skip deduplication if still unhashable
                            pass

                        df.insert(0, '#', range(1, len(df) + 1))

                        ui.label(f'Query Results ({len(df)} records):').classes('text-sm font-semibold mb-2')

                        # Configure table columns
                        columns = []
                        for col in df.columns:
                            if col == '#':
                                # Index column - minimal width, no header label
                                columns.append({
                                    'name': col,
                                    'label': '',
                                    'field': col,
                                    'sortable': True,
                                    'align': 'center',
                                    'style': 'width: 1%; white-space: nowrap; padding: 4px 8px;',
                                    'headerStyle': 'width: 1%; padding: 4px 8px;'
                                })
                            else:
                                # Data columns - auto-width with wrapping
                                columns.append({'name': col, 'label': col, 'field': col, 'sortable': True, 'align': 'left'})

                        # Render results table
                        ui.table(
                            columns=columns,
                            rows=df.to_dict('records'),
                            row_key='#'
                        ).classes('w-full').props('dense flat').style('max-height: 400px;')

        # Input field - fixed at bottom
        with ui.row().classes('w-full gap-2 px-4 pb-4'):
            # Event handlers - submit_question is now synchronous
            def handle_submit():
                submit_question(input_field.value)

            input_field = ui.input(placeholder='Ask a question...').classes('flex-grow input-field').props(
                'outlined rounded'
            ).on('keydown.enter', handle_submit)

            # Add send button inside the input field using 'append' slot (modern pattern)
            with input_field.add_slot('append'):
                send_button = ui.button(
                    icon='send',
                    on_click=handle_submit
                ).props('flat round dense').classes('send-button')

    # Return UI control callbacks
    def clear_chat_ui():
        """Clear all messages from chat container."""
        chat_container.clear()

    return clear_chat_ui, submit_question
