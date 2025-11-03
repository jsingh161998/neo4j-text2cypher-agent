"""LLM factory for multi-provider support."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from neo4j_agent.utils.config import LLMSettings


def create_llm(settings: LLMSettings) -> BaseChatModel:
    """Create LLM instance based on provider settings.

    API keys are loaded from environment variables:
    - OpenAI: LLM_API_KEY or OPENAI_API_KEY
    - Azure: AZURE_OPENAI_API_KEY

    All other settings come from YAML config.

    Args:
        settings: LLM configuration settings

    Returns:
        Configured LLM instance

    Raises:
        ValueError: If provider is not supported
    """
    if settings.provider == "openai":
        # API key from env: LLM_API_KEY or OPENAI_API_KEY
        return ChatOpenAI(
            model=settings.model,
            temperature=settings.temperature,
            max_retries=3,
            request_timeout=60,
        )
    elif settings.provider == "azure_openai":
        # API key from env: AZURE_OPENAI_API_KEY
        # Other settings from YAML config
        return AzureChatOpenAI(
            model=settings.model,
            temperature=settings.temperature,
            azure_endpoint=settings.azure_endpoint,
            azure_deployment=settings.azure_deployment,
            api_version=settings.api_version or "2024-02-01",
            max_retries=3,
            request_timeout=60,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.provider}")
