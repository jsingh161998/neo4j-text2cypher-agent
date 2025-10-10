"""Conversation history utilities for accessing LangGraph checkpoints."""

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver


def get_conversation_history(
    checkpointer: BaseCheckpointSaver,
    config: RunnableConfig,
    max_history: int = 10,
    include_answers: bool = False,
) -> list[dict[str, str]]:
    """Get recent conversation history from checkpointer.

    Retrieves only questions that passed guardrails (no error) and have generated Cypher.

    Args:
        checkpointer: LangGraph checkpointer instance
        config: LangGraph config containing thread_id (passed from workflow.invoke())
        max_history: Maximum number of previous Q&A pairs to retrieve
        include_answers: If True, include final_answer in history (increases token cost)

    Returns:
        List of dicts with 'question', 'cypher_query', and optionally 'final_answer'
        in chronological order (oldest first)
    """
    # Extract thread_id from config (provided by caller during workflow.invoke())
    thread_id = config.get("configurable", {}).get("thread_id")

    if not thread_id:
        return []

    # Get all checkpoints for this thread
    try:
        history = list(checkpointer.list({"configurable": {"thread_id": thread_id}}))
    except Exception:
        # If checkpointer access fails, return empty history
        return []

    # Extract successful question-cypher pairs
    context = []
    seen_questions = set()

    # Iterate from newest to oldest
    for checkpoint in history:
        # CheckpointTuple has 'checkpoint' attribute containing the state
        checkpoint_state = checkpoint.checkpoint.get("channel_values", {})

        question = checkpoint_state.get("question")
        cypher_query = checkpoint_state.get("cypher_query")
        error = checkpoint_state.get("error")

        # Only include if:
        # 1. Question exists and is new
        # 2. No error (passed guardrails)
        # 3. Has generated cypher
        if question and question not in seen_questions and not error and cypher_query:
            pair = {"question": question, "cypher_query": cypher_query}

            # Optionally include final answer
            if include_answers:
                final_answer = checkpoint_state.get("final_answer")
                if final_answer:
                    pair["final_answer"] = final_answer

            context.append(pair)
            seen_questions.add(question)

            # Stop once we have enough
            if len(context) >= max_history:
                break

    # Return in chronological order (oldest first)
    return list(reversed(context))


def format_history_for_prompt(history: list[dict[str, str]], prefix: str = "Recent conversation history") -> str:
    """Format conversation history for inclusion in prompts.

    Args:
        history: List of question-cypher pairs from get_conversation_history()
        prefix: Header text for the history section

    Returns:
        Formatted string ready for prompt inclusion (empty string if no history)
    """
    if not history:
        return ""

    formatted = f"\n\n{prefix}:\n"
    for pair in history:
        formatted += f"  Q: {pair['question']}\n"
        formatted += f"  Cypher: {pair['cypher_query']}\n"

        # Include answer if available
        if "final_answer" in pair:
            formatted += f"  Answer: {pair['final_answer']}\n"

    return formatted
