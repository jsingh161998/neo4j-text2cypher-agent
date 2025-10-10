"""Semantic similarity-based Cypher example retriever."""
import os

from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from neo4j_agent.utils.config import AppSettings


class ExampleRetriever:
    """Retrieves Cypher examples using semantic similarity search.

    Uses LangChain's SemanticSimilarityExampleSelector with InMemoryVectorStore
    to select the most relevant few-shot examples based on question similarity.
    """

    def __init__(self, settings: AppSettings):
        """Initialize the similarity-based retriever.

        Args:
            settings: Application settings containing examples and LLM config
        """
        self.settings = settings
        self.k = settings.query_processing.retriever_limit
        self._example_selector = None
        self._initialize_selector()

    def _initialize_selector(self) -> None:
        """Initialize the semantic similarity example selector."""
        # Load examples from config
        examples = self._load_examples_from_config()

        if not examples:
            raise ValueError("No examples found in configuration")

        # Create embeddings using same provider as LLM
        embeddings = self._create_embeddings()

        # Initialize the semantic similarity selector
        self._example_selector = SemanticSimilarityExampleSelector.from_examples(
            examples=examples,
            embeddings=embeddings,
            vectorstore_cls=InMemoryVectorStore,
            k=self.k,
            input_keys=["question"],
        )

    def _create_embeddings(self) -> OpenAIEmbeddings:
        """Create embeddings instance based on LLM provider.

        API keys are loaded from environment variables (same pattern as LLM factory).
        All other settings come from YAML config.

        Returns:
            Embeddings instance
        """
        llm_config = self.settings.llm

        if llm_config.provider == "openai":
            # API key from env: LLM_API_KEY or OPENAI_API_KEY
            # OpenAIEmbeddings will automatically look for these env vars
            return OpenAIEmbeddings(
                model="text-embedding-3-small",  # Default embedding model
            )
        elif llm_config.provider == "azure_openai":
            # API key from env: AZURE_OPENAI_API_KEY
            # Other settings from YAML config
            return OpenAIEmbeddings(
                azure_endpoint=llm_config.azure_endpoint,
                azure_deployment=llm_config.azure_embedding_deployment or "text-embedding-3-small",
                api_version=llm_config.api_version or "2024-02-01",
            )
        else:
            raise ValueError(f"Unsupported provider for embeddings: {llm_config.provider}")

    def _load_examples_from_config(self) -> list[dict]:
        """Load examples from configuration.

        Returns:
            List of examples with 'question' and 'query' keys
        """
        examples = []
        for i, example in enumerate(self.settings.cypher_examples):
            examples.append(
                {
                    "id": f"example_{i}",
                    "question": example.question,
                    "query": example.cypher,
                }
            )
        return examples

    def get_relevant_examples(self, question: str, k: int | None = None) -> str:
        """Get the most relevant examples for a given question.

        Args:
            question: The user's question to find similar examples for
            k: Number of examples to return (uses instance default if None)

        Returns:
            Formatted string with the most relevant examples
        """
        if self._example_selector is None:
            raise RuntimeError("Example selector not initialized")

        # Use provided k or instance default
        num_examples = k if k is not None else self.k

        # Get similar examples
        selected_examples = self._example_selector.select_examples({"question": question})

        # Limit to requested number if needed
        if len(selected_examples) > num_examples:
            selected_examples = selected_examples[:num_examples]

        # Format examples for prompt
        return self._format_examples(selected_examples)

    def _format_examples(self, examples: list[dict]) -> str:
        """Format examples for inclusion in prompts.

        Args:
            examples: List of selected examples with 'question' and 'query' keys

        Returns:
            Formatted string ready for prompt inclusion
        """
        if not examples:
            return ""

        formatted_examples = []
        for example in examples:
            formatted_examples.append(
                f"Question: {example['question']}\n" f"Cypher: {example['query']}"
            )

        return "\n\n".join(formatted_examples)