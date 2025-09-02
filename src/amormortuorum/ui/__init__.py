"""
UI helpers for non-blocking notifications.

These utilities are deliberately independent of the actual rendering/UI toolkit
(Arcade, etc.). They provide a simple in-memory queue that the rendering layer
can poll to present toasts/snackbars to the player without blocking gameplay.
"""
from .toast import ToastManager, ToastMessage

__all__ = ["ToastManager", "ToastMessage"]
