"""Workflow streaming module for Neo4j Text2Cypher agent.

Handles LangGraph workflow execution with status bar progress indicator.
Shows: ▶ Running: {step} • {time}s elapsed
"""

import asyncio
import queue
import time
from concurrent.futures import ThreadPoolExecutor

from nicegui import ui


class WorkflowStreamer:
    """Handles LangGraph workflow streaming with status bar progress indicator."""

    def __init__(self, workflow):
        """Initialize streamer.

        Args:
            workflow: Compiled LangGraph workflow
        """
        self.workflow = workflow

    async def stream_workflow(
        self,
        initial_state: dict,
        config: dict,
        progress_bar=None,
        progress_spinner=None,
        steps_container=None,
    ) -> dict:
        """Stream workflow execution with status bar.

        Shows single-line status bar: "▶ Running: {step} • {time}s elapsed"
        Tracks step data for final execution summary (no live step tree).

        Args:
            initial_state: Workflow initial state
            config: Workflow config (with thread_id)
            progress_bar: NiceGUI label for status bar
            progress_spinner: NiceGUI spinner component
            steps_container: Not used (kept for compatibility)

        Returns:
            Final workflow state with _execution_details
        """
        return await self._stream_with_status_bar(
            initial_state,
            config,
            progress_bar,
            progress_spinner,
            steps_container
        )

    async def _stream_with_status_bar(
        self,
        initial_state: dict,
        config: dict,
        progress_bar,
        progress_spinner,
        steps_container,
    ) -> dict:
        """Stream workflow with status bar (simplified - no live step tree)."""
        # Track state
        final_state = None
        step_labels = {}  # node_name -> {"start_time": float, "completed": bool, ...}
        overall_start_time = time.time()
        current_step_name = None

        # Create queue for streaming chunks
        chunk_queue = queue.Queue()

        # Run workflow stream in background thread
        def run_workflow_stream():
            """Run workflow stream and put chunks in queue."""
            try:
                for chunk in self.workflow.stream(
                    initial_state,
                    config,
                    stream_mode=["values", "debug"],
                    subgraphs=True
                ):
                    chunk_queue.put(chunk)
                chunk_queue.put(None)  # Signal completion
            except Exception as e:
                chunk_queue.put(("error", e))

        # Start streaming in background
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(run_workflow_stream)

        # Helper function to update status bar (simplified - no step counting)
        def update_status_bar():
            """Update status bar with current progress."""
            if progress_bar and current_step_name:
                elapsed = time.time() - overall_start_time
                # Simplified: Just step name + elapsed time (no step counting)
                status_text = f"Running: {current_step_name.replace('_', ' ').title()} • {elapsed:.1f}s elapsed"
                progress_bar.set_text(status_text)
                # Spinner is visible during execution
            elif progress_bar and progress_spinner:
                # Completed - just hide everything
                progress_bar.set_visibility(False)
                progress_spinner.set_visibility(False)

        # Process chunks as they arrive
        while True:
            # Get next chunk with timeout
            try:
                chunk = await asyncio.to_thread(chunk_queue.get, timeout=0.5)
            except:
                # Timeout - continue waiting
                continue

            # Check for completion or error
            if chunk is None:
                break
            if isinstance(chunk, tuple) and chunk[0] == "error":
                raise chunk[1]

            namespace, mode, data = chunk

            # Use debug mode events to track task start/completion
            if mode == "debug":
                event_type = data.get('type', 'unknown')
                payload = data.get('payload', {})

                # Use debug events to detect task start/end
                if event_type == "task":
                    task_name = payload.get('name', '')
                    # Skip internal nodes
                    if task_name and not task_name.startswith('__'):
                        is_subgraph = bool(namespace)

                        # Extract parent node name from namespace if subgraph
                        parent_node = None
                        if is_subgraph and namespace:
                            parent_node = namespace[0].split(':')[0]

                        # Task started - TRACK DATA ONLY (don't render live labels)
                        if task_name not in step_labels:
                            step_labels[task_name] = {
                                "start_time": time.time(),
                                "completed": False,
                                "is_subgraph": is_subgraph,
                                "parent_node": parent_node
                            }

                            # Update status bar for ALL nodes (main and subgraph)
                            if is_subgraph and parent_node:
                                # Format: "Parent → Child"
                                current_step_name = f"{parent_node} → {task_name}"
                            else:
                                current_step_name = task_name
                            update_status_bar()

                elif event_type == "task_result":
                    task_name = payload.get('name', '')
                    if task_name in step_labels and not step_labels[task_name].get("completed"):
                        # Task completed - update data
                        step_info = step_labels[task_name]
                        elapsed = time.time() - step_info["start_time"]
                        is_subgraph = step_info.get("is_subgraph", False)

                        step_info["completed"] = True
                        step_info["duration"] = elapsed

                        # Status bar is updated on task start, no need to update on completion
                        # (next task will update it)

                continue

            elif mode == "values":
                # Track final state (main workflow only)
                if not namespace:
                    final_state = data

        # When workflow completes, clear status bar and spinner
        if progress_bar:
            progress_bar.delete()
        if progress_spinner:
            progress_spinner.delete()

        # Store execution details for rendering in summary
        final_state['_execution_details'] = {
            'elapsed_total': time.time() - overall_start_time,
            'step_labels': step_labels
        }

        return final_state
