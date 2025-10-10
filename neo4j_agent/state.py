"""State models for the Text2Cypher workflow."""
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    """State for the Text2Cypher workflow.

    Attributes:
        messages: Conversation history managed by LangGraph
        question: User's natural language question
        cypher_query: Generated Cypher query
        query_results: Results from Neo4j execution (list of records as dicts)
        final_answer: Natural language answer to return
        error: Error message if any step fails
        retry_count: Number of correction attempts
        validation_history: List of validation error messages from all attempts
        num_examples_used: Number of similar examples retrieved for query generation
        num_history_items: Number of conversation Q&A pairs used for context
        execution_time: Query execution time in seconds
        failed_at_node: Name of the node where workflow failed (if error)

    Note:
        neo4j_result is returned by executor but NOT in state (not checkpointed).
        Access it from workflow output for UI visualization.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    cypher_query: str | None
    query_results: list[dict] | None
    final_answer: str | None
    error: str | None
    retry_count: int
    # Execution metadata (populated during workflow)
    validation_history: list[str] | None
    num_examples_used: int | None
    num_history_items: int | None
    execution_time: float | None
    failed_at_node: str | None