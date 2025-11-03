"""Neo4j graph visualization component for NiceGUI."""

from neo4j_viz.neo4j import from_neo4j
from nicegui import ui

# Default color palette (from reference project)
DEFAULT_COLORS = [
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#96CEB4",
    "#FECA57",
    "#DDA0DD",
    "#98D8C8",
    "#F7DC6F",
    "#BB8FCE",
    "#85C1E2",
    "#FF8CC8",
    "#A8E6CF",
    "#FFA07A",
    "#B0E0E6",
    "#20B2AA",
    "#F4A460",
]


def extract_graph_metadata(result_obj):
    """Extract node and relationship metadata from Neo4j Result object.

    Args:
        result_obj: Neo4j Result object from custom stream

    Returns:
        dict with:
            - node_labels: dict of {label: count}
            - relationship_types: dict of {type: count}
            - label_colors: dict of {label: color_hex}
    """
    try:
        if result_obj is None:
            return None

        # Get graph data from result
        graph = result_obj.graph()

        # Count nodes by label and preserve order of appearance
        node_labels = {}
        unique_labels_ordered = []
        seen_labels = set()

        for node in graph.nodes:
            # Nodes can have multiple labels, count each
            for label in node.labels:
                if label not in seen_labels:
                    unique_labels_ordered.append(label)
                    seen_labels.add(label)
                node_labels[label] = node_labels.get(label, 0) + 1

        # Count relationships by type
        relationship_types = {}
        for rel in graph.relationships:
            rel_type = rel.type
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

        # Assign colors to labels in order of appearance (matching Streamlit)
        label_colors = {}
        for idx, label in enumerate(unique_labels_ordered):
            label_colors[label] = DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]

        return {
            "node_labels": node_labels,
            "relationship_types": relationship_types,
            "label_colors": label_colors,
        }

    except Exception:
        return None


def render_legend(metadata: dict):
    """Render legend showing node labels and relationship types with pill-style badges.

    Args:
        metadata: Graph metadata from extract_graph_metadata()
    """
    if not metadata:
        return

    node_labels = metadata.get("node_labels", {})
    relationship_types = metadata.get("relationship_types", {})
    label_colors = metadata.get("label_colors", {})

    # Calculate total counts (sum all node counts across labels)
    total_nodes = sum(node_labels.values())
    total_relationships = sum(relationship_types.values())

    with ui.column().classes("w-full gap-2"):
        # Title
        ui.markdown("### Results Overview").style("color: var(--neo4j-text-primary); margin-bottom: 0.5rem;")

        # Node Labels Section
        if node_labels:
            ui.markdown(f"#### **Nodes ({total_nodes})**").style(
                "color: var(--neo4j-text-primary); margin-bottom: 0.5rem; font-size: 0.9rem;"
            )
            for label in sorted(node_labels.keys()):
                count = node_labels[label]
                color = label_colors.get(label, "#999999")

                # Pill-style badge using ui.label with inline styles
                ui.label(f"{label} ({count})").style(
                    f"background-color: {color}; "
                    f"color: black; "
                    f"padding: 2px 6px; "
                    f"border-radius: 12px; "
                    f"font-weight: bold; "
                    f"font-size: 0.85rem; "
                    f"display: inline-block; "
                    f"margin-bottom: 0.25rem;"
                )

        # Relationship Types Section
        if relationship_types:
            ui.markdown(f"#### **Relationships ({total_relationships})**").style(
                "color: var(--neo4j-text-primary); margin-bottom: 0.5rem; font-size: 0.9rem;"
            )
            for rel_type in sorted(relationship_types.keys()):
                count = relationship_types[rel_type]

                # Gray pill-style badge using ui.label
                ui.label(f"{rel_type} ({count})").style(
                    "background-color: #E0E0E0; "
                    "color: black; "
                    "padding: 2px 6px; "
                    "border-radius: 12px; "
                    "font-weight: bold; "
                    "font-size: 0.85rem; "
                    "display: inline-block; "
                    "margin-bottom: 0.25rem;"
                )


def render_neo4j_visualization(result_obj, height: int = 600, show_legend: bool = True):
    """
    Render Neo4j graph visualization with optional legend.

    Only renders if result contains graph data (nodes/relationships).
    Returns silently if no graph data exists.

    Args:
        result_obj: Neo4j Result object from custom stream
        height: Height of visualization in pixels
        show_legend: Whether to display legend (default: True)
    """
    try:
        if result_obj is None:
            return

        # Extract metadata for legend
        metadata = extract_graph_metadata(result_obj)

        # Skip rendering if no graph data (metadata is None or empty)
        if not metadata or not metadata.get("node_labels"):
            return  # No nodes = no graph data = skip visualization

        # Create two-column layout: visualization (70%) + legend (30%)
        with ui.row().classes("w-full gap-4"):
            # Left: Visualization
            with ui.column().classes("flex-1"):
                # Create visualization from result
                viz = from_neo4j(result_obj)

                # Apply color coding by node labels
                viz.color_nodes(property="labels", colors=DEFAULT_COLORS)

                # Render to HTML (default force-directed layout)
                html_content = viz.render(max_allowed_nodes=1000)._repr_html_()

                # Use iframe with srcdoc to render HTML with scripts
                import html as html_module

                escaped_html = html_module.escape(html_content)

                iframe_html = f'''
                <iframe
                    srcdoc="{escaped_html}"
                    style="width: 100%; height: {height}px; border: none; overflow: hidden; display: block;"
                    scrolling="no"
                ></iframe>
                '''

                ui.html(iframe_html, sanitize=False).classes("w-full").style(
                    "width: 100% !important; display: block;"
                )

            # Right: Legend (if enabled and metadata available)
            if show_legend and metadata:
                with (
                    ui.column()
                    .classes("w-80")
                    .style(
                        f"background: var(--neo4j-bg-secondary); "
                        f"padding: 1rem; "
                        f"border-radius: 8px; "
                        f"border: 1px solid var(--neo4j-border); "
                        f"height: {height}px; "  # Match visualization height
                        f"overflow-y: auto;"  # Scroll if content exceeds height
                    )
                ):
                    render_legend(metadata)

    except Exception as e:
        # Skip visualization errors, but don't hide critical system errors
        if isinstance(e, (SystemExit, KeyboardInterrupt, MemoryError)):
            raise
        # Silently skip visualization-related errors (missing data, invalid structure, etc.)
        pass
