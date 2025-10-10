"""Execution summary component for Text2Cypher workflow visualization.

Renders detailed execution information including:
- Workflow steps with timing
- Validation attempts and errors
- Execution statistics
- Context usage (examples, conversation history)
"""

from nicegui import ui


def render_execution_summary(final_state: dict, is_error: bool):
    """Render execution summary section (for both success and error cases).

    Args:
        final_state: Workflow final state with execution metadata
        is_error: Whether workflow ended in error (controls expansion)
    """
    execution_details = final_state.get('_execution_details')
    if not execution_details:
        return  # No execution details available

    elapsed_total = execution_details.get('elapsed_total', 0)
    step_labels = execution_details.get('step_labels', {})

    # Expanded on error, collapsed on success
    with ui.expansion(
        f'🔍 Execution Summary ({elapsed_total:.1f}s)',
        value=is_error  # Auto-expand on error
    ).props('dense').classes('w-full mb-2'):

        # Wrap all content in a column with gap-0 to remove default spacing
        with ui.column().classes('gap-0 w-full'):

            # ========================================
            # 1. Workflow Steps Tree
            # ========================================
            ui.label('📋 Workflow Steps').classes('text-sm font-semibold')

            # Sort steps by start time (execution order)
            sorted_steps = sorted(
                step_labels.keys(),
                key=lambda x: step_labels[x]["start_time"]
            )

            for step_name in sorted_steps:
                step_info = step_labels[step_name]
                is_subgraph = step_info.get("is_subgraph", False)
                display_name = step_name.replace('_', ' ').title()
                duration = step_info.get("duration", 0.0)
                completed = step_info.get("completed", False)

                # Format: ALL items indented, subgraph steps get extra indent
                # Color only checkmark and timing (not entire line)
                if is_subgraph:
                    icon_color = '#00C48C' if completed else '#999999'
                    icon = "✓" if completed else "⊘"
                    # Subgraph: double indent (3rem)
                    with ui.row().classes('gap-1').style('margin-left: 3rem; font-size: 0.875rem;'):
                        ui.label(f"└─ {icon}").style(f'color: {icon_color};')
                        ui.label(display_name).style('color: var(--neo4j-text-primary);')
                        ui.label(f"{duration:.1f}s").style('color: var(--neo4j-text-secondary);')
                else:
                    icon_color = '#00C48C' if completed else '#999999'
                    prefix = "✓" if completed else "⊘"
                    # Main workflow: base indent (1.5rem)
                    with ui.row().classes('gap-1').style('margin-left: 1.5rem; font-size: 0.875rem;'):
                        ui.label(prefix).style(f'color: {icon_color};')
                        ui.label(display_name).style('color: var(--neo4j-text-primary);')
                        ui.label(f"{duration:.1f}s").style('color: var(--neo4j-text-secondary);')

            # ========================================
            # 2. Text2Cypher Details (includes validation + results)
            # ========================================
            retry_count = final_state.get('retry_count', 0)
            validation_history = final_state.get('validation_history', [])
            execution_time = final_state.get('execution_time', 0)
            results = final_state.get('query_results', [])

            ui.label('🔧 Text2Cypher').classes('text-sm font-semibold').style('margin-top: 1rem;')

            # Validation status
            if is_error and validation_history:
                # Error case: Show all validation attempts
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("• ❌").style('color: #D43300;')
                    ui.label("Generated Cypher").style('color: var(--neo4j-text-primary);')
                    ui.label(f"Failed after {len(validation_history)} attempt(s)").style('color: #FFA500; font-weight: 500;')
                for error_msg in validation_history:
                    ui.label(error_msg).classes('text-sm').style(
                        'color: var(--neo4j-text-secondary); white-space: pre-wrap; margin-left: 3rem;'
                    )
            elif retry_count == 0:
                # Success on first try
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("• ✓").style('color: #00C48C;')
                    ui.label("Generated Cypher").style('color: var(--neo4j-text-primary);')
                    ui.label("Passed on first attempt").style('color: var(--neo4j-text-secondary);')
            else:
                # Success after corrections (orange indicator for "had issues but recovered")
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("• ⚠️").style('color: #FFA500;')
                    ui.label("Generated Cypher").style('color: var(--neo4j-text-primary);')
                    ui.label(f"Passed after {retry_count} correction(s)").style('color: #FFA500; font-weight: 500;')
                if validation_history:
                    ui.label("Previous errors (resolved):").classes('text-sm').style(
                        'color: var(--neo4j-text-muted); margin-left: 3rem;'
                    )
                    for error_msg in validation_history[:-1]:  # All but last (which passed)
                        ui.label(error_msg).classes('text-sm').style(
                            'color: var(--neo4j-text-muted); white-space: pre-wrap; margin-left: 4.5rem;'
                        )

            # Query execution time (success only)
            if not is_error and execution_time is not None:
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("•").style('color: var(--neo4j-text-muted);')
                    ui.label("Query execution time:").style('color: var(--neo4j-text-primary);')
                    ui.label(f"{execution_time:.2f}s").style('color: var(--neo4j-text-secondary);')

            # Results count (success only) - moved under Text2Cypher
            if not is_error:
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("•").style('color: var(--neo4j-text-muted);')
                    ui.label("Rows returned:").style('color: var(--neo4j-text-primary);')
                    ui.label(f"{len(results)}").style('color: var(--neo4j-text-secondary);')

            # ========================================
            # 3. Context Used
            # ========================================
            num_examples = final_state.get('num_examples_used')
            num_history = final_state.get('num_history_items')

            if num_examples is not None or num_history is not None:
                ui.label('📚 Context Used').classes('text-sm font-semibold').style('margin-top: 1rem;')
                if num_examples is not None:
                    with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                        ui.label("•").style('color: var(--neo4j-text-muted);')
                        ui.label("Similar examples:").style('color: var(--neo4j-text-primary);')
                        ui.label(f"{num_examples}").style('color: var(--neo4j-text-secondary);')
                if num_history is not None:
                    with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                        ui.label("•").style('color: var(--neo4j-text-muted);')
                        ui.label("Conversation history:").style('color: var(--neo4j-text-primary);')
                        ui.label(f"{num_history} previous Q&A").style('color: var(--neo4j-text-secondary);')

            # ========================================
            # 4. Performance Summary (error only)
            # ========================================
            if is_error:
                ui.label('⏱️ Performance').classes('text-sm font-semibold').style('margin-top: 1rem;')
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("•").style('color: var(--neo4j-text-muted);')
                    ui.label("Total time:").style('color: var(--neo4j-text-primary);')
                    ui.label(f"{elapsed_total:.1f}s").style('color: var(--neo4j-text-secondary);')
                failed_node = final_state.get('failed_at_node', 'unknown')
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("•").style('color: var(--neo4j-text-muted);')
                    ui.label("Failed at:").style('color: var(--neo4j-text-primary);')
                    ui.label(failed_node).style('color: #D43300;')
                with ui.row().classes('gap-1').style('margin-left: 1.5rem;'):
                    ui.label("•").style('color: var(--neo4j-text-muted);')
                    ui.label("Status:").style('color: var(--neo4j-text-primary);')
                    ui.label(f"Failed after {len(validation_history)} attempt(s)").style('color: #D43300; font-weight: 500;')
