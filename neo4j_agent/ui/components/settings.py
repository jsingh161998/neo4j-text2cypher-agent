"""Settings modal component for query processing configuration."""

from nicegui import app, ui

from neo4j_agent.utils.config import AppSettings


def create_settings_modal(settings: AppSettings) -> callable:
    """Create settings modal dialog matching existing UI theme.

    Settings are stored per-session in app.storage.client and do not persist to YAML.
    Each session starts with defaults from config.yml and can customize independently.

    Uses same styling as Answer Details expansion:
    - Dark mode: #0e1117 content background, #014063 header
    - Light mode: #f5f5f5 content background, #0A6190 header
    - CSS variables for automatic theming

    Args:
        settings: Application settings (used for default values only)

    Returns:
        Function to open the settings dialog
    """

    def get_session_settings() -> dict:
        """Get current session settings or defaults from config.yml."""
        if "query_settings" not in app.storage.client:
            # Initialize with defaults from YAML
            app.storage.client["query_settings"] = {
                "result_limit": settings.query_processing.result_limit,
                "retriever_limit": settings.query_processing.retriever_limit,
                "conversation_history_limit": settings.query_processing.conversation_history_limit,
                "max_correction_retries": settings.query_processing.max_correction_retries,
                "show_query_results": settings.query_processing.show_query_results,
                "show_visualization": settings.query_processing.show_visualization,
            }
        return app.storage.client["query_settings"]

    def open_settings():
        """Open settings modal dialog."""

        # Load current session settings
        current_settings = get_session_settings()

        # Check if settings are view-only
        view_only = settings.ui.view_only_settings
        disabled_prop = "disable" if view_only else ""

        with ui.dialog() as dialog, ui.card().classes("settings-modal"):
            # Header with dark blue background (matching expansion headers)
            with ui.row().classes("w-full items-center justify-between settings-header"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("tune", size="md")
                    title_text = (
                        "Application Settings (View Only)" if view_only else "Application Settings"
                    )
                    ui.label(title_text).classes("text-h6")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            # Settings content area (Streamlit charcoal in dark mode)
            with ui.column().classes("w-full gap-0 settings-content"):
                # Result Limit
                ui.label("Result Limit").classes("font-semibold mb-1").style(
                    "color: var(--neo4j-text-primary)"
                )
                result_limit_slider = (
                    ui.slider(min=10, max=100, step=10, value=current_settings["result_limit"])
                    .props(
                        f'color="primary" label label-always label-color="primary" {disabled_prop}'
                    )
                    .classes("mb-1 settings-slider")
                )
                ui.label("Maximum number of rows to return from Cypher queries").classes(
                    "text-sm mb-3"
                ).style("color: var(--neo4j-text-secondary)")

                ui.separator().classes("mb-3").style("background: var(--neo4j-border)")

                # Retriever Limit
                ui.label("Example Retriever Limit").classes("font-semibold mb-1").style(
                    "color: var(--neo4j-text-primary)"
                )
                retriever_limit_slider = (
                    ui.slider(min=1, max=10, step=1, value=current_settings["retriever_limit"])
                    .props(
                        f'color="primary" label label-always label-color="primary" {disabled_prop}'
                    )
                    .classes("mb-1 settings-slider")
                )
                ui.label("Number of similar example queries to retrieve").classes(
                    "text-sm mb-3"
                ).style("color: var(--neo4j-text-secondary)")

                ui.separator().classes("mb-3").style("background: var(--neo4j-border)")

                # Conversation History Limit
                ui.label("Conversation History Limit").classes("font-semibold mb-1").style(
                    "color: var(--neo4j-text-primary)"
                )
                history_limit_slider = (
                    ui.slider(
                        min=1, max=10, step=1, value=current_settings["conversation_history_limit"]
                    )
                    .props(
                        f'color="primary" label label-always label-color="primary" {disabled_prop}'
                    )
                    .classes("mb-1 settings-slider")
                )
                ui.label("Number of previous Q&A pairs to include in prompts").classes(
                    "text-sm mb-3"
                ).style("color: var(--neo4j-text-secondary)")

                ui.separator().classes("mb-3").style("background: var(--neo4j-border)")

                # Max Correction Retries
                ui.label("Max Correction Retries").classes("font-semibold mb-1").style(
                    "color: var(--neo4j-text-primary)"
                )
                retries_slider = (
                    ui.slider(
                        min=1, max=5, step=1, value=current_settings["max_correction_retries"]
                    )
                    .props(
                        f'color="primary" label label-always label-color="primary" {disabled_prop}'
                    )
                    .classes("mb-1 settings-slider")
                )
                ui.label("Maximum attempts to fix invalid Cypher queries").classes(
                    "text-sm mb-3"
                ).style("color: var(--neo4j-text-secondary)")

                ui.separator().classes("mb-3").style("background: var(--neo4j-border)")

                # Show Query Results Checkbox
                show_results_checkbox = ui.checkbox(
                    "Show query results table", value=current_settings["show_query_results"]
                )
                if view_only:
                    show_results_checkbox.disable()
                show_results_checkbox.classes("settings-checkbox")
                with ui.row().classes("ml-8"):
                    ui.label("Display results table in Answer Details section").classes(
                        "text-sm"
                    ).style("color: var(--neo4j-text-muted)")

                ui.separator().classes("mb-3").style("background: var(--neo4j-border)")

                # Show Visualization Checkbox
                show_viz_checkbox = ui.checkbox(
                    "Show graph visualization", value=current_settings["show_visualization"]
                )
                if view_only:
                    show_viz_checkbox.disable()
                show_viz_checkbox.classes("settings-checkbox")
                with ui.row().classes("ml-8"):
                    ui.label(
                        "Display interactive graph when results contain nodes/relationships"
                    ).classes("text-sm").style("color: var(--neo4j-text-muted)")

            # Action Buttons (outside content area, at bottom)
            if not view_only:
                ui.separator().style("background: var(--neo4j-border)")

                with ui.row().classes("w-full justify-between p-4"):
                    ui.button(
                        "Reset to Defaults",
                        on_click=lambda: reset_to_defaults(
                            result_limit_slider,
                            retriever_limit_slider,
                            history_limit_slider,
                            retries_slider,
                            show_results_checkbox,
                            show_viz_checkbox,
                        ),
                    ).props("flat").classes("reset-defaults-btn")

                    ui.button(
                        "Save Changes",
                        icon="save",
                        on_click=lambda: save_settings(
                            dialog,
                            result_limit_slider.value,
                            retriever_limit_slider.value,
                            history_limit_slider.value,
                            retries_slider.value,
                            show_results_checkbox.value,
                            show_viz_checkbox.value,
                        ),
                    ).style("background: #0A6190 !important; color: white !important;")

        def reset_to_defaults(
            result_slider,
            retriever_slider,
            history_slider,
            retries_slider,
            show_results_checkbox,
            show_viz_checkbox,
        ):
            """Reset all settings to defaults from config.yml."""
            result_slider.value = settings.query_processing.result_limit
            retriever_slider.value = settings.query_processing.retriever_limit
            history_slider.value = settings.query_processing.conversation_history_limit
            retries_slider.value = settings.query_processing.max_correction_retries
            show_results_checkbox.value = settings.query_processing.show_query_results
            show_viz_checkbox.value = settings.query_processing.show_visualization

        def save_settings(
            dialog,
            result_limit,
            retriever_limit,
            history_limit,
            max_retries,
            show_results,
            show_viz,
        ):
            """Save settings to session storage (per-user, no YAML write)."""
            # Store in session storage (persists until session reset/timeout)
            app.storage.client["query_settings"] = {
                "result_limit": int(result_limit),
                "retriever_limit": int(retriever_limit),
                "conversation_history_limit": int(history_limit),
                "max_correction_retries": int(max_retries),
                "show_query_results": bool(show_results),
                "show_visualization": bool(show_viz),
            }
            dialog.close()
            ui.notify("Settings saved for this session", type="positive", position="top")

        dialog.open()

    return open_settings
