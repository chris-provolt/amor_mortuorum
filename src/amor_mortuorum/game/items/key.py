"""Key item constants and helpers.

In a full game, items would likely be data-driven. For now, use a stable
identifier and keep higher-level logic (e.g., door opening) dependent only on
this identifier, not on a concrete Item class.
"""

# Unique ID for a basic key used on locked doors
KEY_ITEM_ID = "key"
