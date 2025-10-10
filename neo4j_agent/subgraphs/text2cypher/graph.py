"""Text2Cypher subgraph for Cypher generation, validation, correction, and execution."""

from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_neo4j import Neo4jGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, START, END

from neo4j_agent.state import WorkflowState
from neo4j_agent.subgraphs.text2cypher.nodes.generator import create_generator_node
from neo4j_agent.subgraphs.text2cypher.nodes.validator import create_validator_node
from neo4j_agent.subgraphs.text2cypher.nodes.corrector import create_corrector_node
from neo4j_agent.subgraphs.text2cypher.nodes.executor import create_executor_node
from neo4j_agent.utils.config import QueryProcessingSettings
from neo4j_agent.utils.retriever import ExampleRetriever


def create_text2cypher_subgraph(
    llm: BaseChatModel,
    graph: Neo4jGraph,
    retriever: ExampleRetriever,
    schema: str,
    checkpointer: BaseCheckpointSaver,
    query_settings: QueryProcessingSettings,
) -> StateGraph:
    """Create the Text2Cypher subgraph.

    This subgraph handles the Cypher generation → validation → correction → execution loop.
    It encapsulates retry logic and error handling within the subgraph.

    Workflow:
    START → Generator → Validator → [conditional routing]
                                  → [if error + retries left] → Corrector → Validator (loop)
                                  → [if valid] → Executor → END
                                  → [if max retries] → END

    Args:
        llm: Language model instance
        graph: Neo4j graph connection
        retriever: Semantic similarity example retriever
        schema: Neo4j schema string (from get_schema function)
        checkpointer: Checkpointer for accessing conversation history
        query_settings: Query processing settings (result limit, history limit, retry limit, etc.)

    Returns:
        Compiled subgraph (StateGraph)
    """
    # Create routing function with max_retries from settings
    def route_after_validation(
        state: WorkflowState,
    ) -> Literal["corrector", "executor", "__end__"]:
        """Route based on validation results and retry count.

        Args:
            state: Current workflow state

        Returns:
            Next node: "corrector" if error and retries left, "executor" if valid, "__end__" if max retries
        """
        error = state.get("error")
        retry_count = state.get("retry_count", 0)
        max_retries = query_settings.max_correction_retries

        if error:
            # Has errors - check if we can retry
            if retry_count < max_retries:
                return "corrector"
            else:
                # Max retries reached, end workflow with error
                return "__end__"
        else:
            # No errors - execute the query
            return "executor"

    # Create nodes
    generator = create_generator_node(llm, retriever, checkpointer, query_settings)
    validator = create_validator_node(graph, llm, schema, checkpointer, query_settings)
    corrector = create_corrector_node(llm, schema)
    executor = create_executor_node(graph)

    # Build subgraph
    subgraph = StateGraph(WorkflowState)

    # Add nodes
    subgraph.add_node("generator", generator)
    subgraph.add_node("validator", validator)
    subgraph.add_node("corrector", corrector)
    subgraph.add_node("executor", executor)

    # Define edges
    subgraph.add_edge(START, "generator")
    subgraph.add_edge("generator", "validator")
    subgraph.add_conditional_edges("validator", route_after_validation)
    subgraph.add_edge("corrector", "validator")  # Loop back to validator
    subgraph.add_edge("executor", END)

    # Compile subgraph (note: subgraph does NOT get its own checkpointer)
    # The checkpointer is managed by the parent workflow
    return subgraph.compile()
