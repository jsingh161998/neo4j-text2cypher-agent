"""Main LangGraph workflow construction for Text2Cypher agent."""
from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

from neo4j_agent.state import WorkflowState
from neo4j_agent.nodes.guardrails import create_guardrails_node
from neo4j_agent.nodes.summarizer import create_summarizer_node
from neo4j_agent.subgraphs.text2cypher.graph import create_text2cypher_subgraph
from neo4j_agent.utils.config import AppSettings
from neo4j_agent.utils.llm import create_llm
from neo4j_agent.utils.neo4j import create_neo4j_graph
from neo4j_agent.utils.retriever import ExampleRetriever
from neo4j_agent.utils.schema import get_schema


def route_after_guardrails(state: WorkflowState) -> Literal["text2cypher", "__end__"]:
    """Route based on guardrails validation.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "text2cypher" subgraph if valid, "__end__" if out of scope
    """
    if state.get("error"):
        return "__end__"
    return "text2cypher"


def create_text2cypher_workflow(settings: AppSettings | None = None):
    """Create the Text2Cypher workflow graph.

    Args:
        settings: Application settings (if None, loads from environment)

    Returns:
        Compiled LangGraph workflow with checkpointer
    """
    # Load settings if not provided
    if settings is None:
        settings = AppSettings()

    # Create dependencies
    llm = create_llm(settings.llm)
    graph = create_neo4j_graph(settings.neo4j)
    retriever = ExampleRetriever(settings)

    # Get schema with caching
    schema = get_schema(graph, cache_path=settings.schema_cache_path())

    # Create checkpointer (will be shared with nodes for history access)
    checkpointer = InMemorySaver()

    # Create top-level nodes
    guardrails = create_guardrails_node(
        llm, schema, settings.ui.scope_description, checkpointer, settings.query_processing
    )

    summarizer = create_summarizer_node(llm, checkpointer, settings.query_processing)

    # Create Text2Cypher subgraph
    text2cypher_subgraph = create_text2cypher_subgraph(
        llm, graph, retriever, schema, checkpointer, settings.query_processing
    )

    # Build main workflow
    workflow = StateGraph(WorkflowState)

    # Add nodes (subgraph is added as a node)
    workflow.add_node("guardrails", guardrails)
    workflow.add_node("text2cypher", text2cypher_subgraph)
    workflow.add_node("summarizer", summarizer)

    # Define edges
    workflow.add_edge(START, "guardrails")
    workflow.add_conditional_edges("guardrails", route_after_guardrails)
    workflow.add_edge("text2cypher", "summarizer")
    workflow.add_edge("summarizer", END)

    # Compile with memory
    return workflow.compile(checkpointer=checkpointer)