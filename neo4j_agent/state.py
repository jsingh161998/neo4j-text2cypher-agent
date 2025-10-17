"""State models for the Text2Cypher workflow."""
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


def merge_text2cypher_output(
    existing: dict[str, Any] | None,
    updates: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Custom reducer for text2cypher_output field.

    Performs shallow merge to preserve existing fields when nodes
    return partial updates. This prevents field loss when different
    nodes update different parts of the text2cypher_output.

    Example:
        existing = {"cypher_query": "MATCH...", "retry_count": 0}
        updates = {"retry_count": 1}
        result = {"cypher_query": "MATCH...", "retry_count": 1}

    Args:
        existing: Current text2cypher_output in state
        updates: New partial update from node

    Returns:
        Merged dict with all fields preserved
    """
    if existing is None:
        return updates
    if updates is None:
        return existing

    # Shallow merge: updates override existing values for shared keys,
    # but existing keys not in updates are preserved
    return {**existing, **updates}


class Text2CypherOutput(TypedDict):
    """Output from Text2Cypher subgraph execution.

    This encapsulates all data produced by the text2cypher subgraph
    including query generation, validation, correction, and execution.

    Attributes:
        cypher_query: Generated Cypher query
        query_results: Results from Neo4j execution (list of records as dicts)
        execution_time: Query execution time in seconds
        retry_count: Number of correction attempts (0 = first try succeeded)
        query_generation_trace: Complete trace of query generation/correction process
                                Format: [{"attempt": 1, "query": "...", "validation_errors": [...], "source": "generator"|"corrector"}]
        failed_at_node: Which text2cypher node failed (generator/validator/corrector/executor)
    """
    cypher_query: str | None
    query_results: list[dict] | None
    execution_time: float | None
    retry_count: int
    query_generation_trace: list[dict[str, Any]] | None
    failed_at_node: str | None


class WorkflowState(TypedDict):
    """State for the Text2Cypher workflow.

    Attributes:
        messages: Conversation history managed by LangGraph
        question: User's natural language question
        final_answer: Natural language answer to return
        error: Error message if any step fails (from any workflow node)
        text2cypher_output: Nested output from Text2Cypher subgraph (uses custom reducer for safe merging)
        num_examples_used: Number of similar examples retrieved for query generation
        num_history_items: Number of conversation Q&A pairs used for context

    Note:
        neo4j_result is returned by executor but NOT in state (not checkpointed).
        Access it from workflow output for UI visualization.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    final_answer: str | None
    error: str | None

    # Subgraph outputs - uses custom reducer to safely merge partial updates
    text2cypher_output: Annotated[
        Text2CypherOutput | None,
        merge_text2cypher_output
    ]

    # Workflow-level metadata
    num_examples_used: int | None
    num_history_items: int | None