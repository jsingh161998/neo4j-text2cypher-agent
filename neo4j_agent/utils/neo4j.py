"""Neo4j connection and utilities."""
from langchain_neo4j import Neo4jGraph

from neo4j_agent.utils.config import Neo4jSettings


def create_neo4j_graph(settings: Neo4jSettings) -> Neo4jGraph:
    """Create Neo4j graph connection.

    Args:
        settings: Neo4j connection settings

    Returns:
        Neo4jGraph instance
    """
    return Neo4jGraph(
        url=settings.uri,
        username=settings.username,
        password=settings.password,
        database=settings.database,
        enhanced_schema=False,  # Always False for now
    )