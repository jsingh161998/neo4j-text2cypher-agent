"""
Validator node for checking Cypher query syntax, security, and semantic correctness.

Based on LangGraph documentation: https://python.langchain.com/docs/tutorials/graph/#advanced-implementation-with-langgraph
"""

import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_neo4j import Neo4jGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from neo4j_agent.state import WorkflowState
from neo4j_agent.utils.config import QueryProcessingSettings
from neo4j_agent.utils.history import (
    format_history_for_prompt,
    get_conversation_history,
)


# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================


class ValidateCypherOutput(BaseModel):
    """Structured output for LLM-based semantic validation."""

    is_valid: bool = Field(description="Whether the Cypher query is semantically valid")
    errors: list[str] = Field(
        default_factory=list, description="List of semantic error messages (empty if valid)"
    )


# =============================================================================
# Validation Prompt Templates
# =============================================================================


def create_semantic_validation_prompt() -> ChatPromptTemplate:
    """
    Create a Text2Cypher validation prompt template for semantic validation only.

    Returns:
        ChatPromptTemplate: The prompt template
    """

    validate_cypher_system = """
    You are a Cypher expert reviewing the SEMANTIC correctness of a query.
    Your job is to check if the query retrieves the appropriate data that can be used to answer the user's question.

    CRITICAL: Cypher's role is DATA RETRIEVAL, not data processing.
    - The query should return the raw data needed to answer the question
    - Post-processing (formatting, analysis, summarization) happens AFTER the query executes
    - A query is correct if it returns data containing the information requested, even if that data needs further processing
    - If a query returns paths or nodes that contain the labels/properties needed to answer the question, it is correct

    Focus on whether the query gets the right data, not whether it formats or processes that data.

    DO NOT check schema validity, property existence, or label existence - those are handled separately.
    """

    validate_cypher_user = """Check ONLY these semantic issues:

    1. **Does the query match the question's intent?**
       - Is it querying the correct node/relationship types mentioned in the question?
       - Does the pattern structure make sense for what's being asked?
       - IMPORTANT: Do NOT check if specific properties exist - that's handled by Neo4j EXPLAIN separately
       - A query is VALID if it targets the right entities, regardless of which properties it returns

    2. **Are there logical errors?**
       - Undefined variables used in WHERE/RETURN clauses
       - Contradictory conditions (e.g., age < 20 AND age > 60)
       - Incorrect aggregations or groupings

    3. **Are critical elements missing?**
       - Missing ORDER BY for "top N" questions
       - Missing LIMIT for questions asking for specific counts
       - Missing database aggregations (COUNT, SUM, AVG, MAX, MIN) when the question explicitly asks for counts,
         totals, averages, or other statistical computations that should be done in the database

    4. **Semantic context validation:**
       - Based on the conversation context, determine if this question appears to be:
         * Requesting ADDITIONAL information about entities from recent queries
         * EXPANDING or MODIFYING a previous analysis
         * A completely NEW and unrelated topic
       - If the question semantically appears to be building on recent queries:
         * Check if the query appropriately maintains entity context (filters, properties)
       - If context seems missing when it should be present, flag as an error
       - Use semantic understanding, not specific word patterns

    5. **Are there obvious performance issues?**
       - Unintentional cartesian products
       - Patterns that will return excessive data

    DO NOT report errors about:
    - Properties not existing in the schema (the query should work with available properties)
    - Labels not existing in the schema
    - Relationships not existing in the schema
    - Case sensitivity of names
    - Schema-related issues (handled separately)
    - Missing text summarization/analysis (e.g., "summarize the feedback", "categorize these responses")
      - Text analysis happens AFTER data retrieval by downstream LLM processing
    - Missing visualization/formatting logic (visualization is done by the UI with the returned data)

    DATABASE SCHEMA (defines what properties ACTUALLY exist):
    {schema}

    The user's question:
    {question}

    {conversation_context}

    The Cypher statement to validate:
    {cypher}

    VALIDATION RULE: If the user asks for properties that don't exist in the schema above, the query is VALID
    as long as it returns the correct node types. The downstream summarizer will explain what data is available."""

    return ChatPromptTemplate.from_messages(
        [
            ("system", validate_cypher_system),
            ("human", validate_cypher_user),
        ]
    )


# =============================================================================
# Validation Helper Functions
# =============================================================================


def validate_no_writes(cypher_query: str) -> list[str]:
    """
    Check for write operations in Cypher query.

    Args:
        cypher_query: The Cypher query to check

    Returns:
        List of error messages (empty if no writes found)
    """
    errors = []
    dangerous_keywords = [
        r"\bDELETE\b",
        r"\bDETACH DELETE\b",
        r"\bCREATE\b",
        r"\bMERGE\b",
        r"\bSET\b",
        r"\bREMOVE\b",
        r"\bDROP\b",
    ]

    for keyword_pattern in dangerous_keywords:
        if re.search(keyword_pattern, cypher_query, re.IGNORECASE):
            keyword = keyword_pattern.replace(r"\b", "").replace("\\", "")
            errors.append(
                f"Security violation: Query contains dangerous keyword '{keyword}'. "
                "Only read-only queries (MATCH, RETURN, WITH, WHERE) are allowed."
            )
            break  # Only report first violation

    return errors


def validate_syntax(graph: Neo4jGraph, cypher_query: str) -> list[str]:
    """
    Check Cypher syntax using Neo4j EXPLAIN.

    Args:
        graph: Neo4j graph connection
        cypher_query: The Cypher query to validate

    Returns:
        List of error messages (empty if syntax is valid)
    """
    errors = []
    try:
        # Use EXPLAIN to validate syntax without executing
        graph.query(f"EXPLAIN {cypher_query}")
    except Exception as e:
        error_msg = str(e)
        errors.append(f"Syntax error: {error_msg}")

    return errors


# =============================================================================
# Validator Node Factory
# =============================================================================


def create_validator_node(
    graph: Neo4jGraph,
    llm: BaseChatModel,
    schema: str,
    checkpointer: BaseCheckpointSaver,
    query_settings: QueryProcessingSettings,
):
    """Factory to create the Cypher validation node.

    Performs three levels of validation:
    1. Security validation - Ensure no dangerous operations (DELETE, CREATE, etc.)
    2. Syntax validation - Check if Cypher is syntactically valid using Neo4j EXPLAIN
    3. Semantic validation - Use LLM to check logical correctness and context awareness

    Args:
        graph: Neo4j graph connection for syntax checking
        llm: Language model for semantic validation
        schema: Neo4j schema string (from get_schema function)
        checkpointer: Checkpointer for accessing conversation history
        query_settings: Query processing settings (history limit, etc.)

    Returns:
        Validator node function
    """
    # Create LLM validation chain with structured output
    semantic_validation_prompt = create_semantic_validation_prompt()
    validate_chain = semantic_validation_prompt | llm.with_structured_output(
        ValidateCypherOutput, method="function_calling"
    )

    def validate_cypher(state: WorkflowState, config: RunnableConfig) -> dict:
        """Validate the generated Cypher query.

        Args:
            state: Current workflow state
            config: LangGraph config containing thread_id

        Returns:
            State updates with validation results (sets error if invalid, clears if valid)
        """
        cypher_query = state.get("cypher_query")
        question = state.get("question", "")

        if not cypher_query:
            return {"error": "No Cypher query to validate"}

        # Strip whitespace
        cypher_query = cypher_query.strip()

        all_errors = []

        # 1. Security Validation (check first - fastest)
        write_errors = validate_no_writes(cypher_query)
        all_errors.extend(write_errors)

        # 2. Syntax Validation (check with Neo4j)
        syntax_errors = validate_syntax(graph, cypher_query)
        all_errors.extend(syntax_errors)

        # 3. Semantic Validation (use LLM with conversation context)
        # Get conversation history for context-aware validation
        history = get_conversation_history(
            checkpointer,
            config,
            query_settings.conversation_history_limit,
            include_answers=False,
        )

        # Format conversation context
        conversation_context = ""
        if history:
            conversation_context = "Recent queries from this conversation:\n"
            conversation_context += format_history_for_prompt(history, prefix="")

        # Schema is already a formatted string from get_schema()

        # Perform LLM-based semantic validation
        semantic_result = validate_chain.invoke(
            {
                "question": question,
                "cypher": cypher_query,
                "schema": schema,  # Use schema string directly
                "conversation_context": conversation_context,
            }
        )

        # Add semantic errors if any
        if not semantic_result.is_valid:
            all_errors.extend(semantic_result.errors)

        # Return result
        if all_errors:
            # Track validation history for execution summary
            validation_history = state.get("validation_history", [])
            retry_count = state.get("retry_count", 0)
            error_summary = f"Attempt {retry_count + 1}:\n" + "\n".join(f"  - {err}" for err in all_errors)
            validation_history.append(error_summary)

            # Join all errors into single error message
            error_message = "\n".join(f"- {err}" for err in all_errors)
            return {
                "error": error_message,
                "validation_history": validation_history,
                "failed_at_node": "validator"
            }
        else:
            # All validations passed - explicitly clear error
            return {"error": None}

    return validate_cypher
