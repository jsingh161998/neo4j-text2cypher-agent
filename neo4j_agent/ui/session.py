"""Session management for NiceGUI application.

This module handles client-based session tracking to prevent orphaned sessions.
Sessions are tracked by client_id and automatically cleaned up when inactive.
"""

import asyncio
import uuid
from datetime import datetime, timedelta

from nicegui import app, ui

from neo4j_agent.utils.config import AppSettings

# Module-level session tracking (shared across all clients)
# Track by client_id instead of thread_id to prevent orphaned sessions
active_sessions: dict[str, dict] = {}  # {client_id: {thread_id, last_activity, connected_at}}


async def cleanup_inactive_sessions(settings: AppSettings):
    """Background task to clean up inactive sessions.

    Runs every 60 seconds and removes client sessions inactive for configured timeout.
    Uses settings.ui.session_timeout_minutes from config.

    Args:
        settings: Application settings containing session timeout configuration
    """
    timeout_minutes = settings.ui.session_timeout_minutes
    print(f"🔄 Cleanup task started (checking every 60s, timeout={timeout_minutes}m)")
    while True:
        await asyncio.sleep(60)  # Check every minute

        now = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)

        # Debug: Show what we're checking
        print(f"🔍 Cleanup check at {now.strftime('%H:%M:%S')} - Active sessions: {len(active_sessions)}")

        inactive_clients = [
            client_id
            for client_id, session_data in active_sessions.items()
            if now - session_data['last_activity'] > timeout
        ]

        if inactive_clients:
            for client_id in inactive_clients:
                session_data = active_sessions[client_id]
                print(f"🧹 Cleaning up inactive session: client={client_id}, thread={session_data['thread_id']}")
                del active_sessions[client_id]
                # Note: LangGraph MemorySaver keeps data in memory, cleanup is automatic
        else:
            print(f"✓ No inactive sessions to clean up")


class SessionManager:
    """Manages session state for a single client connection.

    Provides methods to:
    - Initialize or restore session from client storage
    - Update activity timestamps
    - Reset chat (clear state and generate new thread)
    - Clean up on disconnect
    """

    def __init__(self):
        """Initialize session manager for current client."""
        self.client_id = ui.context.client.id

        # Check if client already has a thread (for page refreshes)
        if 'thread_id' in app.storage.client:
            self.thread_id = app.storage.client['thread_id']
            print(f"🔄 Existing session restored: client={self.client_id}, thread={self.thread_id}")
        else:
            # Generate new thread ID for new client
            self.thread_id = str(uuid.uuid4())
            app.storage.client['thread_id'] = self.thread_id
            print(f"🆕 New session created: client={self.client_id}, thread={self.thread_id}")

        # Track session by client_id
        active_sessions[self.client_id] = {
            'thread_id': self.thread_id,
            'last_activity': datetime.now(),
            'connected_at': datetime.now()
        }

        # Register disconnect handler
        app.on_disconnect(self._cleanup_on_disconnect)

    def update_activity(self) -> bool:
        """Update last activity timestamp for this client session.

        Returns:
            bool: True if session is active, False if expired
        """
        # If session not in active_sessions, restore it (happens on page refresh)
        if self.client_id not in active_sessions:
            active_sessions[self.client_id] = {
                'thread_id': self.thread_id,
                'last_activity': datetime.now(),
                'connected_at': datetime.now()
            }
            print(f"🔄 Session restored on activity: client={self.client_id}, thread={self.thread_id}")

        # Update activity timestamp
        active_sessions[self.client_id]['last_activity'] = datetime.now()
        return True

    def reset_chat(self, workflow=None, clear_ui_callback=None):
        """Reset chat by clearing LangGraph thread state and UI (no page reload).

        Args:
            workflow: The compiled LangGraph workflow (to access checkpointer)
            clear_ui_callback: Optional callback function to clear the chat UI
        """
        print(f"🔄 Resetting chat: client={self.client_id}, old_thread={self.thread_id}")

        # Clear LangGraph conversation history for this thread
        if workflow and hasattr(workflow, 'checkpointer'):
            try:
                workflow.checkpointer.delete_thread(self.thread_id)
                print(f"✅ Cleared LangGraph state for thread={self.thread_id}")
            except Exception as e:
                print(f"⚠️ Failed to clear LangGraph state: {e}")

        # Clear the UI (chat messages)
        if clear_ui_callback:
            clear_ui_callback()

        # Generate new thread_id for fresh conversation
        old_thread = self.thread_id
        self.thread_id = str(uuid.uuid4())
        app.storage.client['thread_id'] = self.thread_id

        # Update active session with new thread_id
        if self.client_id in active_sessions:
            active_sessions[self.client_id]['thread_id'] = self.thread_id
            active_sessions[self.client_id]['last_activity'] = datetime.now()

        print(f"✅ Reset complete: {old_thread} → {self.thread_id}")
        ui.notify('Chat reset successfully', type='positive')

    def _cleanup_on_disconnect(self):
        """Clean up session when user disconnects."""
        print(f"👋 User disconnected: client={self.client_id}, thread={self.thread_id}")
        if self.client_id in active_sessions:
            del active_sessions[self.client_id]

    def get_config(self, session_settings: dict | None = None) -> dict:
        """Get LangGraph config for this session's thread.

        Includes per-session query settings from client storage if available.

        Args:
            session_settings: Optional pre-fetched session settings (avoids accessing app.storage.client in background tasks)

        Returns:
            dict: LangGraph config with thread_id and session settings
        """
        config = {"configurable": {"thread_id": self.thread_id}}

        # Use provided session_settings or try to fetch from storage (if in UI context)
        if session_settings is not None:
            config["configurable"].update(session_settings)
        elif 'query_settings' in app.storage.client:
            config["configurable"].update(app.storage.client['query_settings'])

        return config
