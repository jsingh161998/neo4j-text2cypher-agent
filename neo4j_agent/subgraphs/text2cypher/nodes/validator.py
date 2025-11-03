"""
Validator node for checking Cypher query syntax, security, and semantic correctness.

Based on LangGraph documentation: https://python.langchain.com/docs/tutorials/graph/#advanced-implementation-with-langgraph
"""

import re

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


# Pydantic Models for Structured Output
class ValidateCypherOutput(BaseModel):
    """Structured output for LLM-based semantic validation."""

    is_valid: bool = Field(description="Whether the Cypher query is semantically valid")
    errors: list[str] = Field(
        default_factory=list, description="List of semantic error messages (empty if valid)"
    )


# Validation Prompt Templates
def create_semantic_validation_prompt() -> ChatPromptTemplate:
    """
    Create a Text2Cypher validation prompt template for semantic validation only.

    Returns:
        ChatPromptTemplate: The prompt template
    """

    validate_cypher_system = """
    You are a Cypher query validator checking for TECHNICAL ERRORS ONLY.

    CRITICAL RULES:
    1. The generator is intelligent and uses ONLY properties that exist in the schema
    2. DO NOT demand properties that don't exist in the schema
    3. DO NOT re-interpret the question - trust the generator's interpretation
    4. Only flag TECHNICAL bugs that would cause query failures
    """

    validate_cypher_user = """Validate this query for TECHNICAL CORRECTNESS.

    Schema (these are the ONLY properties available in the database):
    {schema}

    Question (for context only): {question}
    Query to validate: {cypher}

    {conversation_context}

    Check for these TECHNICAL ERRORS:

    1. **Undefined variables**
       - A variable is used in WHERE/RETURN but never defined in any MATCH clause
       - In "MATCH (x:Label)", the variable "x" IS DEFINED
       - Only flag if a variable appears nowhere in MATCH

    2. **Properties not in schema**
       - Accessing a property that doesn't exist for that node label in the schema
       - Check the schema carefully - only flag if the property is genuinely missing
       - If schema shows a label's properties, accessing other properties is invalid

    3. **Logical contradictions**
       - WHERE conditions that cannot be true simultaneously

    VALIDATION RULES:
    - If a variable appears in MATCH, it IS DEFINED (mark valid)
    - If a property exists in schema for that label, it IS VALID (mark valid)
    - DO NOT demand properties that don't exist in the schema
    - DO NOT question the generator's interpretation of the question
    - Only flag actual technical bugs, not interpretation differences

    Mark as VALID if:
    - All variables are defined in MATCH clauses
    - All properties exist in the schema for their labels
    - No logical contradictions exist"""

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
        from neo4j_agent.utils.state_helpers import (
            create_text2cypher_update,
            get_text2cypher_output,
            update_last_trace_entry,
        )

        text2cypher_output = get_text2cypher_output(state)
        cypher_query = text2cypher_output.get("cypher_query")
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
        )

        # Format conversation context
        conversation_context = ""
        if history:
            conversation_context = "Recent queries from this conversation:\n"
            conversation_context += format_history_for_prompt(history, prefix="")

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
            # Update query generation trace with validation errors
            trace = update_last_trace_entry(state, validation_errors=all_errors)

            # Join all errors into single error message
            error_message = "\n".join(f"- {err}" for err in all_errors)
            return {
                "error": error_message,
                **create_text2cypher_update(
                    query_generation_trace=trace, failed_at_node="validator"
                ),
            }
        else:
            # All validations passed - explicitly clear error
            return {"error": None}

    return validate_cypher
