"""Cypher syntax highlighting using custom Pygments lexer."""

from nicegui import ui
from pygments import highlight
from pygments.formatters import HtmlFormatter

from neo4j_agent.utils.cypher_lexer import CypherLexer


def render_cypher(cypher_query: str, classes: str = "") -> None:
    """Render Cypher code with syntax highlighting using custom lexer.

    Args:
        cypher_query: The Cypher query to render
        classes: Additional CSS classes to apply
    """
    lexer = CypherLexer()

    # Use classes (not inline styles) so we can override with CSS
    formatter = HtmlFormatter(
        noclasses=False,
        cssclass="highlight cypher-code",
        style="monokai",
    )

    # Generate highlighted HTML
    highlighted_html = highlight(cypher_query, lexer, formatter)

    # Custom CSS with Honda project colors
    html_with_styles = f"""
    <div class="cypher-wrapper {classes}">
        {highlighted_html}
    </div>
    <style>
        /* Container styling */
        .cypher-wrapper .highlight {{
            border-radius: 8px;
            margin: 0;
        }}

        .cypher-wrapper pre {{
            margin: 0 !important;
            padding: 12px !important;
            font-size: 0.875rem;
            overflow-x: auto;
            border-radius: 8px;
            background: #2b2b2b !important;  /* Neutral gray background */
        }}

        /* Dark Mode */
        .cypher-wrapper .k {{ color: #FFC450 !important; }}  /* Keywords (clauses, :, .) */
        .cypher-wrapper .nc {{ color: #F96746 !important; }}  /* Labels and relationship types */
        .cypher-wrapper .nd {{ color: #F96746 !important; }}  /* Relationships (if any) */
        .cypher-wrapper .s,
        .cypher-wrapper .s1,
        .cypher-wrapper .s2 {{ color: #90CB62 !important; }}  /* Strings */
        .cypher-wrapper .nv {{ color: #f8f8f2 !important; }}  /* Variables - white like punctuation */
        .cypher-wrapper .na {{ color: #FFAA97 !important; }}  /* Property names */
        .cypher-wrapper .m,
        .cypher-wrapper .mi,
        .cypher-wrapper .mf {{ color: #CCB4FF !important; }}  /* Numbers */
        .cypher-wrapper .nb {{ color: #89ddff !important; }}  /* Built-in functions - light blue */
        .cypher-wrapper .c,
        .cypher-wrapper .c1,
        .cypher-wrapper .cm {{ color: #6a737d !important; font-style: italic; }}  /* Comments */
        .cypher-wrapper .o {{ color: #FFC450 !important; }}  /* Operators - yellow like keywords */
        .cypher-wrapper .p {{ color: #f8f8f2 !important; }}  /* Punctuation - white */

        /* Light Mode */
        body:not(.dark-mode) .cypher-wrapper pre {{
            background: #f5f5f5 !important;
        }}

        body:not(.dark-mode) .cypher-wrapper .k {{ color: #3F7824 !important; }}  /* Keywords, :, . */
        body:not(.dark-mode) .cypher-wrapper .nc {{ color: #D43300 !important; }}  /* Labels/Relationships */
        body:not(.dark-mode) .cypher-wrapper .nd {{ color: #D43300 !important; }}  /* Relationships */
        body:not(.dark-mode) .cypher-wrapper .s,
        body:not(.dark-mode) .cypher-wrapper .s1,
        body:not(.dark-mode) .cypher-wrapper .s2 {{ color: #986400 !important; }}  /* Strings */
        body:not(.dark-mode) .cypher-wrapper .nv {{ color: #212121 !important; }}  /* Variables - dark gray */
        body:not(.dark-mode) .cypher-wrapper .na {{ color: #D43300 !important; }}  /* Property names */
        body:not(.dark-mode) .cypher-wrapper .m,
        body:not(.dark-mode) .cypher-wrapper .mi,
        body:not(.dark-mode) .cypher-wrapper .mf {{ color: #754EC8 !important; }}  /* Numbers */
        body:not(.dark-mode) .cypher-wrapper .nb {{ color: #0A6190 !important; }}  /* Functions */
        body:not(.dark-mode) .cypher-wrapper .c,
        body:not(.dark-mode) .cypher-wrapper .c1,
        body:not(.dark-mode) .cypher-wrapper .cm {{ color: #6a737d !important; font-style: italic; }}  /* Comments */
        body:not(.dark-mode) .cypher-wrapper .o {{ color: #3F7824 !important; }}  /* Operators */
        body:not(.dark-mode) .cypher-wrapper .p {{ color: #212121 !important; }}  /* Punctuation - dark gray */
    </style>
    """

    ui.html(html_with_styles, sanitize=False)
