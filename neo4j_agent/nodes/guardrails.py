"""Guardrails node for validating if questions are in scope."""
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from neo4j_agent.state import WorkflowState
from neo4j_agent.utils.config import QueryProcessingSettings
from neo4j_agent.utils.history import (
    get_conversation_history,
    format_history_for_prompt,
)


# =============================================================================
# Guardrails Prompt
# =============================================================================

GUARDRAILS_SYSTEM = """You must decide whether the provided question is in scope.
Assume the question might be related.
If you're absolutely sure it is NOT related, output "end".
Provide only the specified output: "continue" or "end".

IMPORTANT: When analyzing the current question, consider the conversation history if provided.
Questions that may seem incomplete or out of context on their own could be follow-ups to previous questions.
Use the conversation history to understand the full context before deciding if a question is out of scope."""


# =============================================================================
# Guardrails Node Factory
# =============================================================================


def create_guardrails_node(
    llm: BaseChatModel,
    schema: str,
    scope_description: str,
    checkpointer: BaseCheckpointSaver,
    query_settings: QueryProcessingSettings,
):
    """Factory to create the guardrails validation node.

    Args:
        llm: Language model instance
        schema: Neo4j database schema string
        scope_description: Application scope description
        checkpointer: Checkpointer for accessing conversation history
        query_settings: Query processing settings (history limit, include answers, etc.)

    Returns:
        Guardrails node function
    """

    def validate_question(state: WorkflowState, config: RunnableConfig) -> dict:
        """Validate if the question is in scope for Text2Cypher.

        Args:
            state: Current workflow state
            config: LangGraph config containing thread_id

        Returns:
            State updates with error if question is out of scope
        """
        question = state["question"]

        # Get conversation history from checkpointer using thread_id from config
        history = get_conversation_history(
            checkpointer,
            config,
            query_settings.conversation_history_limit,
            query_settings.include_answers_in_history,
        )
        history_context = format_history_for_prompt(history)

        # Build scope context
        scope_context = (
            f"Use this scope description to inform your decision:\n{scope_description}"
            if scope_description
            else ""
        )

        # Build graph context
        graph_context = f"\n\nUse the graph schema to inform your answer:\n{schema}"

        # Build human message with history
        human_message = (
            scope_context
            + graph_context
            + history_context
            + f"\n\nCurrent Question: {question}"
        )

        # Check with LLM
        messages = [
            SystemMessage(content=GUARDRAILS_SYSTEM),
            HumanMessage(content=human_message),
        ]

        response = llm.invoke(messages)
        answer = response.content.strip().lower()

        # Check if question is valid ("end" means out of scope)
        if "end" in answer:
            return {
                "error": "Question is out of scope for this system. "
                "Please ask questions about data in the graph database.",
                "final_answer": None,
            }

        # Question is valid, continue (clear any previous error)
        return {"error": None}

    return validate_question