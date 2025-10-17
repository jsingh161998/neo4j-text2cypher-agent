"""Conversation history utilities for accessing LangGraph checkpoints."""

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver


def get_conversation_history(
    checkpointer: BaseCheckpointSaver,
    config: RunnableConfig,
    max_history: int = 10,
) -> list[dict[str, str]]:
    """Get recent conversation history from checkpointer.

    Retrieves only questions that passed guardrails (no error) and have generated Cypher.
    Note: Final answers are NOT included in history to reduce token usage.

    Args:
        checkpointer: LangGraph checkpointer instance
        config: LangGraph config containing thread_id (passed from workflow.invoke())
        max_history: Maximum number of previous Q&A pairs to retrieve

    Returns:
        List of dicts with 'question' and 'cypher_query'
        in chronological order (oldest first)
    """
    # Extract thread_id from config (provided by caller during workflow.invoke())
    thread_id = config.get("configurable", {}).get("thread_id")

    if not thread_id:
        return []

    # Get all checkpoints for this thread
    try:
        all_checkpoints = list(checkpointer.list({"configurable": {"thread_id": thread_id}}))
    except Exception:
        # If checkpointer access fails, return empty history
        return []

    # Skip the first checkpoint group (current turn) - LangGraph best practice
    # The first checkpoint represents the current/in-progress turn and should not be included
    # in history context for the current turn's processing
    if not all_checkpoints:
        return []

    # Skip checkpoints from current turn by skipping first occurrence of the current question
    # Get the current question from the first (newest) checkpoint
    first_checkpoint_state = all_checkpoints[0].checkpoint.get("channel_values", {})
    current_question = first_checkpoint_state.get("question")

    # If there's no current question (shouldn't happen), use all checkpoints
    if not current_question:
        history = all_checkpoints
    else:
        # Filter out all checkpoints with the current question
        history = [
            cp
            for cp in all_checkpoints
            if cp.checkpoint.get("channel_values", {}).get("question") != current_question
        ]

    # Extract successful question-cypher pairs
    context = []
    seen_questions = set()

    # Iterate from newest to oldest
    for checkpoint in history:
        # CheckpointTuple has 'checkpoint' attribute containing the state
        checkpoint_state = checkpoint.checkpoint.get("channel_values", {})

        question = checkpoint_state.get("question")
        error = checkpoint_state.get("error")
        final_answer = checkpoint_state.get("final_answer")

        # Access cypher_query from nested text2cypher_output
        text2cypher_output = checkpoint_state.get("text2cypher_output", {})
        cypher_query = text2cypher_output.get("cypher_query") if text2cypher_output else None

        # Only include if:
        # 1. Question exists and is new
        # 2. No error (passed guardrails)
        # 3. Has generated cypher
        # 4. Has final_answer (turn is COMPLETE - this prevents including current turn)
        if (
            question
            and question not in seen_questions
            and not error
            and cypher_query
            and final_answer
        ):
            # Only include question and cypher (not final_answer to save tokens)
            pair = {"question": question, "cypher_query": cypher_query}
            context.append(pair)
            seen_questions.add(question)

            # Stop once we have enough
            if len(context) >= max_history:
                break

    # Return in chronological order (oldest first)
    return list(reversed(context))


def format_history_for_prompt(
    history: list[dict[str, str]], prefix: str = "Recent conversation history"
) -> str:
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

    return formatted
