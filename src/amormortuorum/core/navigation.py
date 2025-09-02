from __future__ import annotations

from enum import Enum


class NextAction(Enum):
    """Navigation outcome from the Run Summary screen.

    TO_GRAVEYARD: Bring the player to the Graveyard hub to start next run,
    rest, manage Crypt, etc.

    TO_MAIN_MENU: Return to the Main Menu screen.
    """

    TO_GRAVEYARD = "to_graveyard"
    TO_MAIN_MENU = "to_main_menu"
