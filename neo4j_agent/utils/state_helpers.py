"""Helper functions for safe state access and updates.

These utilities simplify working with nested text2cypher_output state
and reduce boilerplate in node functions.
"""

from typing import Any

from neo4j_agent.state import Text2CypherOutput, WorkflowState


def get_text2cypher_output(state: WorkflowState) -> dict[str, Any]:
    """Safely get text2cypher_output with default values.

    Returns a dict (not TypedDict) for easier mutation in nodes.
    If text2cypher_output doesn't exist, returns initialized structure.

    Args:
        state: Current workflow state

    Returns:
        Text2cypher output dict with all fields (None/empty defaults if not set)
    """
    return state.get("text2cypher_output") or {
        "cypher_query": None,
        "query_results": None,
        "execution_time": None,
        "retry_count": 0,
        "query_generation_trace": [],
        "failed_at_node": None
    }


def append_to_query_trace(
    state: WorkflowState,
    attempt: int,
    query: str,
    source: str,
    validation_errors: list[str] | None = None
) -> list[dict[str, Any]]:
    """Append entry to query_generation_trace and return complete list.

    Args:
        state: Current workflow state
        attempt: Attempt number (1-indexed)
        query: Cypher query string
        source: Source of query ("generator" or "corrector")
        validation_errors: List of validation error messages (empty/None if valid)

    Returns:
        Complete query_generation_trace list with new entry appended
    """
    output = get_text2cypher_output(state)
    trace = output.get("query_generation_trace") or []

    # Append new entry
    trace.append({
        "attempt": attempt,
        "query": query,
        "validation_errors": validation_errors or [],
        "source": source
    })

    return trace


def update_last_trace_entry(
    state: WorkflowState,
    **updates
) -> list[dict[str, Any]]:
    """Update the last entry in query_generation_trace.

    Useful for validator adding validation_errors to most recent attempt.

    Args:
        state: Current workflow state
        **updates: Key-value pairs to update in last entry

    Returns:
        Complete query_generation_trace list with last entry updated

    Raises:
        IndexError: If trace is empty
    """
    output = get_text2cypher_output(state)
    trace = output.get("query_generation_trace") or []

    if not trace:
        raise IndexError("Cannot update last trace entry: trace is empty")

    # Update last entry
    trace[-1].update(updates)

    return trace


def create_text2cypher_update(**fields) -> dict[str, dict[str, Any]]:
    """Create a text2cypher_output update dict for returning from nodes.

    This helper ensures consistent update structure and makes node returns cleaner.

    Args:
        **fields: Field names and values to update in text2cypher_output

    Returns:
        Dict formatted for state update: {"text2cypher_output": {...}}

    Example:
        return create_text2cypher_update(
            cypher_query=query,
            retry_count=1,
            query_generation_trace=trace
        )
    """
    return {"text2cypher_output": fields}
