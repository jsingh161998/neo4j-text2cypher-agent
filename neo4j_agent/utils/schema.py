"""Neo4j schema management with caching."""
import json
from pathlib import Path

from langchain_neo4j import Neo4jGraph


def get_schema(graph: Neo4jGraph, cache_path: str | Path | None = None) -> str:
    """Get Neo4j schema with optional caching.

    Args:
        graph: Neo4jGraph connection instance
        cache_path: Optional path to cache file (e.g., "cache/schema.json")

    Returns:
        Schema string with node properties, relationship properties, and relationships
    """
    cache_path = Path(cache_path) if cache_path else None

    # Try to load from cache first
    if cache_path and cache_path.exists():
        try:
            with open(cache_path) as f:
                cached = json.load(f)
                print(f"Loaded schema from cache: {cache_path}")
                return cached["schema"]
        except Exception as e:
            print(f"Warning: Failed to load schema cache: {e}")

    # Fetch schema from Neo4j
    print("Fetching schema from Neo4j...")
    schema = graph.schema

    # Save to cache if path provided
    if cache_path:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump({"schema": schema}, f, indent=2)
            print(f"Saved schema to cache: {cache_path}")
        except Exception as e:
            print(f"Warning: Failed to save schema cache: {e}")

    return schema


def refresh_schema_cache(graph: Neo4jGraph, cache_path: str | Path) -> str:
    """Force refresh of schema cache.

    Args:
        graph: Neo4jGraph connection instance
        cache_path: Path to cache file

    Returns:
        Refreshed schema string
    """
    cache_path = Path(cache_path)

    # Delete existing cache
    if cache_path.exists():
        cache_path.unlink()
        print(f"Deleted old schema cache: {cache_path}")

    # Fetch and save new schema
    return get_schema(graph, cache_path)