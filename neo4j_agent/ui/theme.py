"""Neo4j-inspired theme for NiceGUI application.

This module provides custom Neo4j colors, fonts, and CSS styling with dark mode support.
"""

from nicegui import ui


def setup_neo4j_theme():
    """Set up custom Neo4j-inspired theme with working dark mode."""

    # Set NiceGUI color palette to Neo4j colors
    ui.colors(
        primary='#0A6190',    # Neo4j Blue (Baltic-50)
        secondary='#5DB3BF',  # Light blue
        accent='#8FE3E8',     # Accent blue
        positive='#3F7824',   # Success green
        negative='#D43300',   # Error red
        warning='#FFC450',    # Warning yellow
        info='#014063',       # Dark blue
    )

    # Add custom CSS for Neo4j-inspired styling and dark mode support
    # Start in dark mode by default (prevents flash)
    ui.add_head_html('''
        <script>
            // Set dark mode immediately before page renders to prevent flash
            document.documentElement.classList.add('dark-mode');
            if (document.body) {
                document.body.classList.add('dark-mode');
            } else {
                document.addEventListener('DOMContentLoaded', function() {
                    document.body.classList.add('dark-mode');
                });
            }
        </script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&display=swap');

            /* Apply Neo4j font globally */
            body, .q-btn, .q-field, .q-item {
                font-family: 'Public Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            }

            /* CSS Variables for theming */
            :root {
                /* Light mode colors */
                --neo4j-bg-primary: #ffffff;
                --neo4j-bg-secondary: #e8eaed;
                --neo4j-text-primary: #212325;
                --neo4j-text-secondary: #666666;
                --neo4j-text-muted: #999999;
                --neo4j-border: #e2e3e5;
            }

            /* Dark mode colors */
            body.dark-mode {
                --neo4j-bg-primary: #1a1a1a;
                --neo4j-bg-secondary: #252a2e;
                --neo4j-text-primary: #ffffff;
                --neo4j-text-secondary: #cccccc;
                --neo4j-text-muted: #999999;
                --neo4j-border: #444444;
            }

            /* Apply smooth transitions */
            body, .themed-element {
                transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
            }

            /* Prevent body scrollbar for fixed-height layout */
            body {
                overflow: hidden;
            }

            /* Ensure page container fills viewport */
            .q-page-container {
                overflow: hidden;
            }

            /* Override Quasar defaults for dark mode */
            body.dark-mode .q-header {
                background: var(--neo4j-blue) !important;
            }

            body.dark-mode .q-page-container {
                background: var(--neo4j-bg-primary) !important;
            }

            /* Force button text colors in dark mode - target button AND all children */
            body.dark-mode .example-question-btn,
            body.dark-mode .example-question-btn *,
            body.dark-mode .example-question-btn .q-btn__content,
            body.dark-mode .example-question-btn .block {
                color: #ffffff !important;
            }

            body.dark-mode .example-question-btn {
                background: #333333 !important;
            }

            /* Button text colors in light mode - target button AND all children */
            .example-question-btn,
            .example-question-btn *,
            .example-question-btn .q-btn__content,
            .example-question-btn .block {
                color: #0A6190 !important;
            }

            .example-question-btn {
                background: #E7F3F8 !important;
            }

            /* Input field styling for dark mode */
            body.dark-mode .input-field .q-field__control,
            body.dark-mode .input-field input {
                color: white !important;
            }

            body.dark-mode .input-field .q-field__control:before,
            body.dark-mode .input-field .q-field__control:after {
                border-color: white !important;
            }

            body.dark-mode .input-field .q-field__native::placeholder {
                color: rgba(255, 255, 255, 0.5) !important;
            }

            /* Input field styling for light mode */
            .input-field .q-field__control,
            .input-field input {
                color: #000000 !important;
            }

            .input-field .q-field__control:before {
                border-color: #e2e3e5 !important;
            }

            .input-field.q-field--focused .q-field__control:before,
            .input-field.q-field--focused .q-field__control:after {
                border-color: #0A6190 !important;
            }

            .input-field .q-field__native::placeholder {
                color: rgba(0, 0, 0, 0.75) !important;
            }

            /* Modern send button inside input field */
            /* Dark mode - white icon, blue background on hover */
            body.dark-mode .send-button .q-icon {
                color: white !important;
            }

            body.dark-mode .send-button:hover {
                background-color: #0A6190 !important;
            }

            /* Light mode - Neo4j blue icon, light blue on hover */
            .send-button .q-icon {
                color: #0A6190 !important;
            }

            .send-button:hover {
                background-color: rgba(10, 97, 144, 0.1) !important;
            }

            /* Separator styling - visible in dark mode */
            body.dark-mode .q-separator {
                background: rgba(255, 255, 255, 0.2) !important;
            }

            .q-separator {
                background: var(--neo4j-border) !important;
            }

            /* Table theming for dark mode */
            body.dark-mode .q-table {
                background: var(--neo4j-bg-primary) !important;
                color: var(--neo4j-text-primary) !important;
            }

            body.dark-mode .q-table tbody tr {
                background: var(--neo4j-bg-primary) !important;
            }

            body.dark-mode .q-table thead tr,
            body.dark-mode .q-table thead th {
                background: #014063 !important;
                color: white !important;
                border: 1px solid var(--neo4j-border) !important;
            }

            body.dark-mode .q-table tbody td {
                color: var(--neo4j-text-primary) !important;
                border: 1px solid var(--neo4j-border) !important;
            }

            body.dark-mode .q-table tbody tr:hover {
                background: #333333 !important;
            }

            /* Increase header and cell font sizes */
            body.dark-mode .q-table thead th {
                font-size: 0.95rem !important;
                font-weight: 600 !important;
            }

            body.dark-mode .q-table tbody td {
                font-size: 0.8rem !important;
            }

            /* Table theming for light mode */
            .q-table {
                background: #ffffff !important;
                color: var(--neo4j-text-primary) !important;
            }

            .q-table thead tr,
            .q-table thead th {
                background: #0A6190 !important;
                color: white !important;
                border: 1px solid var(--neo4j-border) !important;
                font-size: 0.95rem !important;
                font-weight: 600 !important;
            }

            .q-table tbody td {
                color: var(--neo4j-text-primary) !important;
                border: 1px solid var(--neo4j-border) !important;
                font-size: 0.8rem !important;
            }

            .q-table tbody tr:hover {
                background: var(--neo4j-bg-secondary) !important;
            }

            /* Pulse animation for active workflow steps */
            @keyframes pulse {
                0%, 100% {
                    opacity: 1;
                }
                50% {
                    opacity: 0.5;
                }
            }

            .active-step {
                animation: pulse 1.5s ease-in-out infinite;
            }

            /* Expansion background - always visible (not just on hover) */
            body.dark-mode .q-expansion-item {
                background: var(--neo4j-bg-secondary) !important;
                border-radius: 4px;
                margin-left: 16px !important;
                margin-right: 16px !important;
                margin-bottom: 8px !important;
            }

            .q-expansion-item {
                background: var(--neo4j-bg-secondary) !important;
                border-radius: 4px;
                margin-left: 16px !important;
                margin-right: 16px !important;
                margin-bottom: 8px !important;
            }

            /* Expansion header - dark blue (matching header) for contrast */
            body.dark-mode .q-expansion-item__container > .q-item {
                background: #014063 !important;
                border-radius: 4px 4px 0 0;
            }

            .q-expansion-item__container > .q-item {
                background: #0A6190 !important;
                border-radius: 4px 4px 0 0;
                color: white !important;
            }

            /* Expansion header text - white in light mode */
            .q-expansion-item__container > .q-item * {
                color: white !important;
            }

            /* Expansion content area - lighter background */
            body.dark-mode .q-expansion-item__container .q-expansion-item__content {
                background: var(--neo4j-bg-secondary) !important;
                border-radius: 0 0 4px 4px;
            }

            .q-expansion-item__container .q-expansion-item__content {
                background: var(--neo4j-bg-secondary) !important;
                border-radius: 0 0 4px 4px;
            }

            /* Answer expansion - dark charcoal background in dark mode (Streamlit-style) */
            body.dark-mode .q-expansion-item:has([aria-label*="Answer"]:not([aria-label*="Details"])) .q-expansion-item__content {
                background: #0e1117 !important;
            }

            /* Keep white in light mode */
            .q-expansion-item:has([aria-label*="Answer"]:not([aria-label*="Details"])) .q-expansion-item__content {
                background: #ffffff !important;
            }

            /* Answer Details expansion - same dark charcoal (Streamlit-style) */
            body.dark-mode .q-expansion-item:has([aria-label*="Answer Details"]) .q-expansion-item__content {
                background: #0e1117 !important;
            }

            .q-expansion-item:has([aria-label*="Answer Details"]) .q-expansion-item__content {
                background: #ffffff !important;
            }

            /* Execution Details/Summary expansion - same dark charcoal (Streamlit-style) */
            body.dark-mode .q-expansion-item:has([aria-label*="Execution Details"]) .q-expansion-item__content,
            body.dark-mode .q-expansion-item:has([aria-label*="Execution Summary"]) .q-expansion-item__content {
                background: #0e1117 !important;
            }

            .q-expansion-item:has([aria-label*="Execution Details"]) .q-expansion-item__content,
            .q-expansion-item:has([aria-label*="Execution Summary"]) .q-expansion-item__content {
                background: #ffffff !important;
            }

            /* Cypher code block - slightly lighter gray (Streamlit-style) */
            body.dark-mode .cypher-code-block pre {
                background: #262c36 !important;
                border: none !important;
                box-shadow: none !important;
                outline: none !important;
                border-radius: 4px;
                padding: 12px !important;
            }

            .cypher-code-block pre {
                background: #f5f5f5 !important;
                border: none !important;
                box-shadow: none !important;
                outline: none !important;
                border-radius: 4px;
                padding: 12px !important;
            }

            /* Remove outer container border/background/outline */
            body.dark-mode .cypher-code-block,
            body.dark-mode .cypher-code-block * {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                outline: none !important;
            }

            .cypher-code-block,
            .cypher-code-block * {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                outline: none !important;
            }

            /* Ensure pre element shows */
            body.dark-mode .cypher-code-block pre {
                background: #1e1e1e !important;
            }

            .cypher-code-block pre {
                background: #f5f5f5 !important;
            }

            /* Fix syntax highlighting colors for better contrast */
            /* Dark mode - lighter colors for readability */
            body.dark-mode .cypher-code-block .hljs-string,
            body.dark-mode .cypher-code-block .hljs-attr,
            body.dark-mode .cypher-code-block .hljs-template-variable {
                color: #98c379 !important;  /* Light green for strings */
            }

            body.dark-mode .cypher-code-block .hljs-keyword,
            body.dark-mode .cypher-code-block .hljs-selector-tag,
            body.dark-mode .cypher-code-block .hljs-literal {
                color: #c678dd !important;  /* Light purple for keywords */
            }

            body.dark-mode .cypher-code-block .hljs-number {
                color: #d19a66 !important;  /* Orange for numbers */
            }

            body.dark-mode .cypher-code-block .hljs-comment {
                color: #5c6370 !important;  /* Gray for comments */
            }

            /* Table cell wrapping - headers stay single line, body cells wrap */
            .q-table {
                table-layout: auto !important;
            }

            /* Headers - keep on one line for readability */
            .q-table thead th {
                white-space: nowrap !important;
            }

            /* Body cells - wrap long content */
            .q-table tbody td {
                white-space: normal !important;
                word-wrap: break-word !important;
                word-break: break-word !important;
                overflow-wrap: anywhere !important;
            }

            /* ============================================
               Settings Modal Styling (Streamlit Theme)
               ============================================ */

            /* Modal card - responsive sizing with no default padding */
            .settings-modal {
                min-width: min(90vw, 600px) !important;
                max-width: 650px !important;
                max-height: 85vh !important;
                overflow-y: auto !important;
                border-radius: 8px !important;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
                background: var(--neo4j-bg-primary) !important;
                padding: 0 !important;  /* Remove default card padding */
            }

            /* Settings header (dark blue bar matching expansion headers) */
            body.dark-mode .settings-header {
                background: #014063 !important;  /* Same as expansion headers */
                border-radius: 8px 8px 0 0 !important;
                padding: 20px 24px !important;
                margin: 0 !important;
            }

            .settings-header {
                background: #0A6190 !important;  /* Light mode header */
                border-radius: 8px 8px 0 0 !important;
                padding: 20px 24px !important;
                margin: 0 !important;
            }

            /* Header text and icons - white color */
            .settings-header * {
                color: white !important;
            }

            /* Settings content area (Streamlit charcoal in dark mode) */
            body.dark-mode .settings-content {
                background: #0e1117 !important;  /* Same as Answer Details expansion */
                padding: 24px !important;
                margin: 0 !important;
            }

            .settings-content {
                background: #f5f5f5 !important;  /* Light gray in light mode */
                padding: 24px !important;
                margin: 0 !important;
            }

            /* Bottom action buttons area */
            .settings-modal > .q-card__section:last-child {
                border-radius: 0 0 8px 8px !important;
            }

            /* Reset to Defaults button styling - target button content */
            body.dark-mode .reset-defaults-btn,
            body.dark-mode .reset-defaults-btn *,
            body.dark-mode .reset-defaults-btn .q-btn__content {
                color: #ffffff !important;  /* White in dark mode */
            }

            .reset-defaults-btn,
            .reset-defaults-btn *,
            .reset-defaults-btn .q-btn__content {
                color: #0A6190 !important;  /* Neo4j blue in light mode */
            }

            /* Slider styling - Neo4j blue */
            body.dark-mode .settings-slider .q-slider__track-container--h .q-slider__selection {
                background: #0A6190 !important;
            }

            body.dark-mode .settings-slider .q-slider__thumb {
                color: #0A6190 !important;
            }

            .settings-slider .q-slider__track-container--h .q-slider__selection {
                background: #0A6190 !important;
            }

            .settings-slider .q-slider__thumb {
                color: #0A6190 !important;
            }

            /* Note: Slider labels styled via label-color="primary" prop in settings.py */

            /* Checkbox styling - Neo4j blue when checked */
            body.dark-mode .settings-checkbox .q-checkbox__bg {
                border-color: var(--neo4j-border) !important;
            }

            body.dark-mode .settings-checkbox.q-checkbox--truthy .q-checkbox__bg {
                background: #0A6190 !important;
                border-color: #0A6190 !important;
            }

            body.dark-mode .settings-checkbox .q-checkbox__label {
                color: var(--neo4j-text-primary) !important;
            }

            .settings-checkbox .q-checkbox__bg {
                border-color: #666666 !important;
            }

            .settings-checkbox.q-checkbox--truthy .q-checkbox__bg {
                background: #0A6190 !important;
                border-color: #0A6190 !important;
            }

            /* Radio button styling - Neo4j blue when selected */
            body.dark-mode .settings-radio .q-radio__label {
                color: var(--neo4j-text-primary) !important;
            }

            .settings-radio .q-radio__label {
                color: var(--neo4j-text-primary) !important;
            }

            /* Dialog backdrop */
            body.dark-mode .q-dialog__backdrop {
                background: rgba(0, 0, 0, 0.7) !important;
            }

            .q-dialog__backdrop {
                background: rgba(0, 0, 0, 0.5) !important;
            }

        </style>
    ''')


class ThemeToggle:
    """Manages theme switching between light and dark modes.

    Provides a toggle button that switches between light and dark themes
    and updates the icon accordingly.
    """

    def __init__(self):
        """Initialize theme toggle in dark mode (default)."""
        self.is_dark = True

    def create_toggle_button(self) -> ui.icon:
        """Create theme toggle button icon.

        Returns:
            ui.icon: The theme toggle icon button
        """
        self.icon = ui.icon('light_mode', size='md').classes('cursor-pointer text-white')
        self.icon.on('click', self.toggle)
        return self.icon

    def toggle(self):
        """Toggle between light and dark mode."""
        self.is_dark = not self.is_dark
        if self.is_dark:
            # Switch to dark mode
            ui.run_javascript('document.body.classList.add("dark-mode")')
            self.icon.props('name=light_mode')
        else:
            # Switch to light mode
            ui.run_javascript('document.body.classList.remove("dark-mode")')
            self.icon.props('name=dark_mode')
