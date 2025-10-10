"""
Executor node for running Cypher queries against Neo4j.

Based on LangGraph documentation: https://python.langchain.com/docs/tutorials/graph/#advanced-implementation-with-langgraph
"""

import time
from typing import Any

from langchain_neo4j import Neo4jGraph
from langgraph.config import get_stream_writer
from neo4j import Query

from neo4j_agent.state import WorkflowState

# Try to import LangChain's sanitization function
try:
    from langchain_neo4j.graphs.neo4j_graph import _value_sanitize

    HAS_SANITIZE = True
except ImportError:
    HAS_SANITIZE = False


# =============================================================================
# Executor Node Factory
# =============================================================================


def create_executor_node(graph: Neo4jGraph):
    """Factory to create the Cypher execution node.

    Executes validated Cypher queries against Neo4j and returns both:
    - Records (list of dicts) for data processing
    - Result object for visualization (has .graph() method)

    Args:
        graph: Neo4j graph connection

    Returns:
        Executor node function
    """

    def execute_cypher(state: WorkflowState) -> dict:
        """Execute the Cypher query against Neo4j.

        Uses LangGraph's custom streaming to emit non-serializable Neo4j Result object.
        The Result object is sent via custom stream (not checkpointed) for UI visualization.

        Args:
            state: Current workflow state

        Returns:
            State updates with query results (serializable only)
        """
        cypher_query = state.get("cypher_query", "")

        if not cypher_query or not cypher_query.strip():
            return {
                "query_results": [],
                "error": "No Cypher query to execute",
            }

        # Execute query with session approach to get Result object for visualization
        try:
            # Track execution time
            start_time = time.time()

            with graph._driver.session(database=graph._database) as session:
                result_obj = session.run(Query(text=cypher_query, timeout=graph.timeout))
                records = [r.data() for r in result_obj]

                # Sanitize values if enabled
                if graph.sanitize and HAS_SANITIZE:
                    records = [_value_sanitize(el) for el in records]

            execution_time = time.time() - start_time

            # Emit neo4j_result via custom stream (bypasses checkpointing)
            writer = get_stream_writer()
            writer({"neo4j_result": result_obj})

            # Return only serializable state updates
            return {
                "query_results": records if records else [],
                "execution_time": execution_time,
                "error": None,  # Clear any previous errors
            }

        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            return {
                "query_results": [],
                "error": error_msg,
                "failed_at_node": "executor"
            }

    return execute_cypher