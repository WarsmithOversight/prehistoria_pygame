# event_bus.py

class EventBus:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type, listener):
        """Register a listener function for a specific event type."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def post(self, event_type, data=None):
        """Post an event to all registered listeners."""
        if event_type in self.listeners:
            for listener in self.listeners[event_type]:
                listener(data)