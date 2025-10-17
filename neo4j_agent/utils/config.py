"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseModel):
    """LLM provider settings.

    All configuration (provider, model, temperature, Azure settings) comes from YAML.
    Only API keys are loaded from environment variables via LLM factory.
    """

    provider: Literal["openai", "azure_openai"]
    model: str
    temperature: float = 0.0
    # Azure-specific settings (required if provider is azure_openai)
    azure_endpoint: str | None = None
    azure_deployment: str | None = None
    azure_embedding_deployment: str | None = None
    api_version: str | None = None


class Neo4jSettings(BaseSettings):
    """Neo4j connection settings.

    Connection credentials (uri, username, password) must be set via environment variables.
    Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD in .env file.
    """

    uri: str
    username: str
    password: str
    database: str = Field(default="neo4j")

    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env", extra="ignore")


class CypherExample(BaseModel):
    """Cypher example for few-shot learning."""

    question: str
    cypher: str


class QueryProcessingSettings(BaseSettings):
    """Query processing settings (loaded from YAML only)."""

    result_limit: int = Field(default=50)
    retriever_limit: int = Field(default=10)
    conversation_history_limit: int = Field(default=10)
    max_correction_retries: int = Field(default=3)  # Maximum correction attempts for invalid Cypher

    model_config = SettingsConfigDict(extra="ignore")


class UISettings(BaseSettings):
    """UI and application scope settings (loaded from YAML only)."""

    title: str = Field(default="Neo4j Text2Cypher Agent")
    scope_description: str = Field(default="")
    example_questions: list[str] = Field(default_factory=list)
    session_timeout_minutes: int = Field(default=10)
    view_only_settings: bool = Field(default=False)  # If true, settings modal is read-only

    model_config = SettingsConfigDict(extra="ignore")


class AppSettings(BaseSettings):
    """Application settings.

    Configuration hierarchy:
    - LLM settings: YAML only (provider, model, temperature, Azure config)
    - Neo4j settings: YAML for database name, ENV for credentials (uri, username, password)
    - API keys: ENV only (LLM_API_KEY, OPENAI_API_KEY, AZURE_OPENAI_API_KEY)
    - UI/Query settings: YAML only
    """

    llm: LLMSettings
    neo4j: Neo4jSettings
    query_processing: QueryProcessingSettings = Field(default_factory=QueryProcessingSettings)
    ui: UISettings = Field(default_factory=UISettings)
    cypher_examples: list[CypherExample] = Field(default_factory=list)
    config_file_path: Path  # Store config location for schema cache path

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="ignore")

    def schema_cache_path(self) -> str:
        """Get schema cache path relative to config directory.

        Pattern: {config_dir}/neo4j_database_schema/{database}_schema.json
        Example: app-config/honda/neo4j_database_schema/honda_schema.json
        """
        config_dir = self.config_file_path.parent
        return str(config_dir / "neo4j_database_schema" / f"{self.neo4j.database}_schema.json")

    @classmethod
    def from_yaml(cls, yaml_path: str | Path = "app-config/config.yml") -> "AppSettings":
        """Load settings from YAML file.

        LLM settings loaded entirely from YAML (no env override).
        Neo4j credentials loaded from ENV (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD).
        """
        yaml_path = Path(yaml_path).resolve()  # Make absolute
        if not yaml_path.exists():
            msg = f"Configuration file not found: {yaml_path}"
            raise FileNotFoundError(msg)

        with open(yaml_path) as f:
            config_data = yaml.safe_load(f) or {}

        # LLM settings from YAML only (required)
        llm_data = config_data.get("llm")
        if not llm_data:
            msg = "LLM configuration is required in app-config/config.yml"
            raise ValueError(msg)
        llm_settings = LLMSettings(**llm_data)

        # UI settings from YAML only
        ui_data = config_data.get("ui", {})
        ui_settings = UISettings(**ui_data)

        # Query processing settings from YAML only
        query_processing_data = config_data.get("query_processing", {})
        query_processing_settings = QueryProcessingSettings(**query_processing_data)

        # Cypher examples from YAML (aliased as example_queries)
        example_queries_data = config_data.get("example_queries", [])
        cypher_examples = [CypherExample(**ex) for ex in example_queries_data]

        # Neo4j database name from YAML, credentials from ENV
        neo4j_data = config_data.get("neo4j", {})
        neo4j_settings = Neo4jSettings(**neo4j_data)

        return cls(
            llm=llm_settings,
            neo4j=neo4j_settings,
            ui=ui_settings,
            query_processing=query_processing_settings,
            cypher_examples=cypher_examples,
            config_file_path=yaml_path,  # Store the path
        )
