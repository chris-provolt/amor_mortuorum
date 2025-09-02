class EventType:
    """Centralized event type names used across the application."""

    # Emitted when a single relic's toggle state changes
    RELIC_TOGGLE_CHANGED = "relic.toggle.changed"

    # Emitted when the aggregate relic passive modifiers have changed
    RELIC_PASSIVES_CHANGED = "relic.passives.changed"
