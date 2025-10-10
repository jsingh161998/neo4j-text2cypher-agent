"""
Corrector node for fixing invalid Cypher queries using LLM feedback.

Based on LangGraph documentation: https://python.langchain.com/docs/tutorials/graph/#advanced-implementation-with-langgraph
"""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from neo4j_agent.state import WorkflowState


# =============================================================================
# Correction Prompt Templates
# =============================================================================


def create_correction_prompt_template() -> ChatPromptTemplate:
    """
    Create a Text2Cypher query correction prompt template.

    Returns:
        ChatPromptTemplate: The prompt template
    """
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a Cypher expert reviewing a statement written by a junior developer. "
                    "You need to correct the Cypher statement based on the provided errors. No pre-amble."
                    "Do not wrap the response in any backticks or anything else. Respond with a Cypher statement only!"
                ),
            ),
            (
                "human",
                """Check for invalid syntax or semantics and return a corrected Cypher statement.

IMPORTANT: Be VERY careful when checking the schema - the errors you received might be incorrect!

SPECIAL VALIDATION RULES (ignore errors about these):
- String literals in WHERE clauses or functions are NOT label names - they are just string values
- When you see patterns like tolower(x) = tolower("some_string"), the "some_string" is a string value, not a label
- Only actual label references like (:LabelName) or n:LabelName need to match the schema
- String values being compared or processed should NOT be changed to match schema labels
- Dynamic label checking (e.g., using labels(n) function) is for runtime matching - keep the original strings

CRITICAL INSTRUCTIONS FOR READING THE SCHEMA:
- The schema shows node labels with their properties
- Labels and properties are CASE SENSITIVE - use them EXACTLY as shown in the schema
- DO NOT modify or "correct" label names - if the error says a label doesn't exist, check the schema for the exact spelling
- When correcting based on errors, ensure you're using the exact label/property names from the schema

To verify if a property exists before "correcting" it:
1. Find the node label in the schema
2. Look at ALL properties listed for that node (shown in curly braces)
3. If you see the property listed, that property EXISTS for that node
4. If the error says "Property 'x' does not exist" but you find it in the schema, IGNORE that error - the property DOES exist

Schema:
{schema}

Note: Do not include any explanations or apologies in your responses.
Do not wrap the response in any backticks or anything else.
Respond with a Cypher statement only!

Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.

The question is:
{question}

The Cypher statement is:
{cypher}

The errors are:
{errors}

Corrected Cypher statement: """,
            ),
        ]
    )


# =============================================================================
# Corrector Node Factory
# =============================================================================


def create_corrector_node(llm: BaseChatModel, schema: dict[str, Any]):
    """Factory to create the Cypher correction node.

    Uses LLM to fix invalid Cypher queries based on error messages.

    Args:
        llm: Language model instance
        schema: Neo4j schema dictionary (with "schema" key containing string representation)

    Returns:
        Corrector node function
    """
    correction_prompt = create_correction_prompt_template()
    correction_chain = correction_prompt | llm | StrOutputParser()

    def correct_cypher(state: WorkflowState) -> dict:
        """Correct an invalid Cypher query.

        Args:
            state: Current workflow state

        Returns:
            State updates with corrected Cypher query and incremented retry count
        """
        question = state["question"]
        cypher_query = state.get("cypher_query", "")
        error = state.get("error", "")
        retry_count = state.get("retry_count", 0)

        # Schema is already a formatted string from get_schema()

        # Generate corrected Cypher
        corrected_cypher = correction_chain.invoke(
            {
                "question": question,
                "cypher": cypher_query,
                "errors": error,
                "schema": schema,  # Use schema string directly
            }
        )

        # Increment retry count to track correction attempts
        # This is used by the subgraph routing to determine if max retries reached
        new_retry_count = retry_count + 1

        # Return corrected query and updated retry count
        # Note: error field is NOT cleared here - validator will clear it if correction is valid
        return {
            "cypher_query": corrected_cypher,
            "retry_count": new_retry_count,
        }

    return correct_cypher
