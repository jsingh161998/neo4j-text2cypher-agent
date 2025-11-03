"""Generator node for converting natural language to Cypher queries."""

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
from neo4j_agent.utils.retriever import ExampleRetriever


# Generation Prompt Templates
def create_generation_prompt_template(result_limit: int) -> ChatPromptTemplate:
    """Create Text2Cypher generation prompt template.

    Args:
        result_limit: Maximum number of rows to return in query results

    Returns:
        The prompt template
    """
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Given an input question, convert it to a Cypher query. No pre-amble. "
                    "Do not wrap the response in any backticks or anything else. Respond with a Cypher statement only! "
                    "Always include a LIMIT clause to prevent excessive results unless the question specifically asks for all results."
                ),
            ),
            (
                "human",
                f"""You are a Neo4j expert. Given an input question, create a syntactically correct Cypher query to run.
Do not wrap the response in any backticks or anything else. Begin with MATCH or WITH clauses only. Respond with a Cypher statement only!

IMPORTANT: Always end your query with LIMIT {result_limit} unless the question specifically asks for all results or a different number.

CONTEXT RULES:
- Analyze the semantic intent of the question:
  * Is this requesting ADDITIONAL information about the same entities from recent queries?
  * Is this EXPANDING or MODIFYING a previous analysis?
  * Is this a COMPLETELY NEW topic or question?
  * Does this question only make sense with context from recent queries?

- When "Recent queries from this conversation" are provided at the end of examples:
  * Understand the conversation flow and topic continuity
  * IMPORTANT: If recent queries filtered by specific entities or properties,
    and the current question seems to be adding/expanding the analysis, MAINTAIN those filters
  * When a question appears to be requesting more information in the same context, preserve entity filters
    even if the specific attributes being queried are different
  * Only treat as independent if the question explicitly mentions DIFFERENT entities or is clearly unrelated
  * Trust your language understanding to determine when context is relevant

- Examples of semantic intent (not rigid patterns):
  * Continuation: Brief questions that expand on previous topics
  * Reference: Questions using pronouns or incomplete references
  * Addition: Questions requesting more data about the same entities
  * New Topic: Complete questions about different entities or analyses

- Maintain consistency with node labels, properties, and patterns from the examples
- DO NOT invent new node types or properties - use only patterns shown in the examples

Below are example questions and their corresponding Cypher queries. These are your ONLY reference for valid patterns:

{{fewshot_examples}}

User input: {{question}}
Cypher query:""",
            ),
        ]
    )


# =============================================================================
# Generator Node Factory
# =============================================================================


def create_generator_node(
    llm: BaseChatModel,
    retriever: ExampleRetriever,
    checkpointer: BaseCheckpointSaver,
    query_settings: QueryProcessingSettings,
):
    """Factory to create the Cypher generation node.

    Args:
        llm: Language model instance
        retriever: Semantic similarity example retriever
        checkpointer: Checkpointer for accessing conversation history
        query_settings: Query processing settings (default values, can be overridden by session)

    Returns:
        Generator node function
    """

    def generate_cypher(state: WorkflowState, config: RunnableConfig) -> dict:
        """Generate a Cypher query from natural language question.

        Args:
            state: Current workflow state
            config: LangGraph config containing thread_id and optional session settings

        Returns:
            State updates with generated Cypher query
        """
        question = state["question"]

        # Get session settings from config (runtime), fallback to defaults
        configurable = config.get("configurable", {})
        result_limit = configurable.get("result_limit", query_settings.result_limit)
        conversation_history_limit = configurable.get(
            "conversation_history_limit", query_settings.conversation_history_limit
        )

        # Create prompt with runtime result_limit
        generation_prompt = create_generation_prompt_template(result_limit)
        text2cypher_chain = generation_prompt | llm | StrOutputParser()

        # Get semantically similar examples (uses retriever's configured k)
        # Note: retriever returns formatted string, so we track count from config
        examples = retriever.get_relevant_examples(question)
        num_examples = configurable.get("retriever_limit", query_settings.retriever_limit)

        # Get conversation history from checkpointer using thread_id from config
        history = get_conversation_history(
            checkpointer,
            config,
            conversation_history_limit,
        )

        # Append conversation history to examples (treated as additional examples)
        if history:
            history_context = format_history_for_prompt(
                history, prefix="Recent queries from this conversation"
            )
            full_examples = examples + history_context
        else:
            full_examples = examples

        # Generate Cypher query
        generated_cypher = text2cypher_chain.invoke(
            {
                "question": question,
                "fewshot_examples": full_examples,
            }
        )

        # Initialize text2cypher_output with query generation trace
        from neo4j_agent.utils.state_helpers import append_to_query_trace, create_text2cypher_update

        trace = append_to_query_trace(
            state,
            attempt=1,
            query=generated_cypher,
            source="generator",
            validation_errors=[],  # No errors yet, validator will check
        )

        return {
            **create_text2cypher_update(
                cypher_query=generated_cypher,
                retry_count=0,
                query_generation_trace=trace,
                query_results=None,
                execution_time=None,
                failed_at_node=None,
            ),
            "num_examples_used": num_examples,
            "num_history_items": len(history),
        }

    return generate_cypher
