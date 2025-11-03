"""Execution summary component for Text2Cypher workflow visualization.

Renders execution information including:
- Agent execution steps with timing (marks failed steps with ❌)
- Text2Cypher execution statistics (only if text2cypher nodes executed)
"""

from nicegui import ui

from neo4j_agent.ui.components.cypher_highlight import render_cypher


def render_execution_summary(final_state: dict, is_error: bool):
    """Render execution summary section (for both success and error cases).

    Args:
        final_state: Workflow final state with execution metadata
        is_error: Whether workflow ended in error (controls expansion)
    """
    execution_details = final_state.get("_execution_details")
    if not execution_details:
        return  # No execution details available

    elapsed_total = execution_details.get("elapsed_total", 0)
    step_labels = execution_details.get("step_labels", {})

    # Expanded on error, collapsed on success
    expansion_summary = (
        ui.expansion(value=is_error).props("dense").classes("w-full mb-2 execution-summary-expansion")
    )  # Auto-expand on error
    with expansion_summary:
        # Custom header with icon
        with expansion_summary.add_slot("header"), ui.row().classes("items-center gap-2"):
            ui.icon("troubleshoot", size="sm").classes("material-symbols-outlined").style(
                "color: #90A4AE !important;"
            )
            ui.label(f"Execution Summary ({elapsed_total:.1f}s)").classes("text-sm")
        # Wrap all content in a column with gap-0 to remove default spacing
        with ui.column().classes("gap-0 w-full"):
            # ========================================
            # 1. Agent Execution Tree
            # ========================================
            ui.label("Agent Execution").classes("text-sm font-semibold")

            # Sort steps by start time (execution order)
            sorted_steps = sorted(step_labels.keys(), key=lambda x: step_labels[x]["start_time"])

            # Get failed node name to mark with red X (check nested structure)
            text2cypher_output = final_state.get("text2cypher_output", {})
            failed_at = text2cypher_output.get("failed_at_node")

            for step_name in sorted_steps:
                step_info = step_labels[step_name]
                is_subgraph = step_info.get("is_subgraph", False)
                display_name = step_name.replace("_", " ").title()
                duration = step_info.get("duration", 0.0)
                completed = step_info.get("completed", False)
                is_failed_node = step_name == failed_at

                # Determine icon and color based on status
                if is_failed_node:
                    icon = "❌"
                    icon_color = "#D43300"  # red
                elif completed:
                    icon = "✓"
                    icon_color = "#00C48C"  # green
                else:
                    icon = "⊘"
                    icon_color = "#999999"  # gray

                # Format: ALL items indented, subgraph steps get extra indent
                # Color only checkmark and timing (not entire line)
                if is_subgraph:
                    # Subgraph: double indent (3rem)
                    with ui.row().classes("gap-1").style("margin-left: 3rem; font-size: 0.875rem;"):
                        ui.label(f"└─ {icon}").style(f"color: {icon_color};")
                        ui.label(display_name).style("color: var(--neo4j-text-primary);")
                        ui.label(f"{duration:.1f}s").style("color: var(--neo4j-text-secondary);")
                else:
                    # Main workflow: base indent (1.5rem)
                    with (
                        ui.row().classes("gap-1").style("margin-left: 1.5rem; font-size: 0.875rem;")
                    ):
                        ui.label(icon).style(f"color: {icon_color};")
                        ui.label(display_name).style("color: var(--neo4j-text-primary);")
                        ui.label(f"{duration:.1f}s").style("color: var(--neo4j-text-secondary);")

            # ========================================
            # 2. Text2Cypher Details (only if text2cypher nodes executed)
            # ========================================
            # Check if text2cypher subgraph actually executed
            executed_nodes = set(step_labels.keys())
            text2cypher_nodes = {"generator", "validator", "corrector", "executor"}
            text2cypher_executed = bool(executed_nodes & text2cypher_nodes)

            # Only show Text2Cypher section if it ran
            if text2cypher_executed:
                execution_time = text2cypher_output.get("execution_time", 0)
                results = text2cypher_output.get("query_results", [])

                ui.label("Text2Cypher").classes("text-sm font-semibold").style("margin-top: 1rem;")

                # Query execution time (success only)
                if not is_error and execution_time is not None:
                    with ui.row().classes("gap-1").style("margin-left: 1.5rem;"):
                        ui.label("•").style("color: var(--neo4j-text-muted);")
                        ui.label("Query execution time:").style("color: var(--neo4j-text-primary);")
                        ui.label(f"{execution_time:.2f}s").style(
                            "color: var(--neo4j-text-secondary);"
                        )

                # Results count (success only)
                if not is_error and results is not None:
                    with ui.row().classes("gap-1").style("margin-left: 1.5rem;"):
                        ui.label("•").style("color: var(--neo4j-text-muted);")
                        ui.label("Rows returned:").style("color: var(--neo4j-text-primary);")
                        ui.label(f"{len(results)}").style("color: var(--neo4j-text-secondary);")

                # ========================================
                # 3. Query Generation Trace (only if corrections occurred)
                # ========================================
                query_trace = text2cypher_output.get("query_generation_trace", [])
                if query_trace and len(query_trace) > 1:
                    ui.label("Query Generation Trace").classes("text-sm font-semibold").style(
                        "margin-top: 1rem;"
                    )

                    for entry in query_trace:
                        attempt_num = entry.get("attempt", "?")
                        source = entry.get("source", "unknown")
                        query = entry.get("query", "N/A")
                        validation_errors = entry.get("validation_errors", [])

                        # Attempt header
                        ui.label(f"Attempt {attempt_num}").classes("text-sm font-semibold").style(
                            "margin-left: 1.5rem; margin-top: 0.5rem; "
                            "color: var(--neo4j-text-primary);"
                        )

                        # Source label
                        ui.label(f"{source.title()} produced:").classes("text-xs").style(
                            "margin-left: 3rem; color: var(--neo4j-text-secondary);"
                        )

                        # Query code block with syntax highlighting
                        with ui.element("div").style("margin-left: 3rem; max-height: 150px; overflow-y: auto;"):
                            render_cypher(query, classes="text-xs")

                        # Validation result
                        if validation_errors:
                            ui.label("❌ Validation: Failed").classes("text-xs").style(
                                "margin-left: 3rem; color: #D43300; font-weight: 500;"
                            )
                            for error in validation_errors:
                                ui.label(f"• {error}").classes("text-xs").style(
                                    "margin-left: 4.5rem; color: var(--neo4j-text-secondary);"
                                )
                        else:
                            ui.label("✓ Validation: Passed").classes("text-xs").style(
                                "margin-left: 3rem; color: #00C48C; font-weight: 500;"
                            )
