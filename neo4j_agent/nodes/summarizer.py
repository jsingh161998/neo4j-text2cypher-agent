"""Summarizer node for converting Cypher query results to natural language answers.

Based on LangGraph documentation: https://python.langchain.com/docs/tutorials/graph/#advanced-implementation-with-langgraph
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from neo4j_agent.state import WorkflowState
from neo4j_agent.utils.config import QueryProcessingSettings
from neo4j_agent.utils.history import (
    format_history_for_prompt,
    get_conversation_history,
)


# =============================================================================
# Summarization Prompt Template
# =============================================================================


def create_summarization_prompt() -> ChatPromptTemplate:
    """Create a summarization prompt template.

    Returns:
        ChatPromptTemplate for summarizing query results
    """
    system_message = """You are a helpful assistant that summarizes database query results
into clear, natural language answers.

Your job is to take the raw data returned from a database query and present it in a way
that directly answers the user's question."""

    user_message = """Query Results:
{results}

{conversation_context}

Question: {question}

Instructions:
* Summarize the query results as a direct answer to the question
* When results are not empty, assume the question is valid and the answer is truthful
* Do not add helpful text, apologies, or preambles
* Do not start with "Here is a summary" or "Based on the results"
* If there are multiple results, format them in a clear list or structured format
* Don't report empty string results, but DO include numeric results that are 0 or 0.0
* If the question uses pronouns referring to previous context (like "those", "them", "it"),
  use the conversation history to provide proper context in your response
* If results are empty or no data was found, say: "No data found matching your criteria."

Provide a concise, direct answer:"""

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("human", user_message),
        ]
    )


# =============================================================================
# Summarizer Node Factory
# =============================================================================


def create_summarizer_node(
    llm: BaseChatModel,
    checkpointer: BaseCheckpointSaver,
    query_settings: QueryProcessingSettings,
):
    """Factory to create the summarization node.

    Converts Cypher query results into natural language answers using an LLM.
    Includes conversation history for context-aware responses.

    Args:
        llm: Language model for generating summaries
        checkpointer: Checkpointer for accessing conversation history
        query_settings: Query processing settings (history limit, etc.)

    Returns:
        Summarizer node function
    """
    # Create summarization chain
    summarization_prompt = create_summarization_prompt()
    summarize_chain = summarization_prompt | llm | StrOutputParser()

    def summarize(state: WorkflowState, config: RunnableConfig) -> dict:
        """Summarize Cypher query results into a natural language answer.

        Args:
            state: Current workflow state
            config: LangGraph config containing thread_id

        Returns:
            State updates with final_answer
        """
        question = state.get("question", "")
        query_results = state.get("query_results")

        # Handle empty or missing results
        if not query_results:
            return {"final_answer": "No data found matching your criteria."}

        # Get conversation history for context
        history = get_conversation_history(
            checkpointer,
            config,
            query_settings.conversation_history_limit,
            include_answers=query_settings.include_answers_in_history,
        )

        # Format conversation context
        conversation_context = ""
        if history:
            conversation_context = "Previous conversation context:\n"
            conversation_context += format_history_for_prompt(history, prefix="")

        # Generate summary
        summary = summarize_chain.invoke(
            {
                "question": question,
                "results": query_results,
                "conversation_context": conversation_context,
            }
        )

        return {"final_answer": summary}

    return summarize
