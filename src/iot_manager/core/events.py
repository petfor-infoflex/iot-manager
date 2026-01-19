"""Event system for decoupled communication between components."""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events that can be emitted."""

    # Device events
    DEVICE_DISCOVERED = "device_discovered"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEVICE_STATE_CHANGED = "device_state_changed"
    DEVICE_REMOVED = "device_removed"

    # Discovery events
    DISCOVERY_STARTED = "discovery_started"
    DISCOVERY_STOPPED = "discovery_stopped"

    # Application events
    SETTINGS_CHANGED = "settings_changed"
    APP_MINIMIZED = "app_minimized"
    APP_RESTORED = "app_restored"


@dataclass
class Event:
    """An event with type and associated data."""

    type: EventType
    data: Any = None


class EventBus:
    """Simple event bus for publish/subscribe communication."""

    def __init__(self):
        self._subscribers: dict[EventType, list[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from events of a specific type.

        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.type}: {e}")

    def publish_async(self, event: Event, gui_callback: Callable) -> None:
        """Publish an event and schedule GUI update on main thread.

        Args:
            event: The event to publish
            gui_callback: Function to schedule callbacks on GUI thread
        """
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    gui_callback(lambda cb=callback: cb(event))
                except Exception as e:
                    logger.error(f"Error scheduling event handler for {event.type}: {e}")
