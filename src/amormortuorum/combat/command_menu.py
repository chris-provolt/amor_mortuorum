from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

from .actions import Action, Command

logger = logging.getLogger(__name__)


class MenuState(Enum):
    """Internal state of the command menu."""

    MENU = auto()
    TARGET_SELECT = auto()
    COMPLETE = auto()


# Which commands require a target selection step
REQUIRES_TARGET = {Command.ATTACK, Command.SKILL}


@dataclass(frozen=True)
class Target:
    """Represents a selectable target in combat.

    This is a minimal interface to decouple UI from game data models.
    """

    id: str
    name: str
    alive: bool = True


@dataclass(frozen=True)
class SelectionResult:
    """Simple result value object returned by the menu when complete."""

    command: Command
    target_id: Optional[str] = None


class CommandMenu:
    """Stateful controller for the combat command menu and target selector.

    This class contains no rendering code and is unit-testable. It models a
    simple state machine that supports navigating the main command list and
    (when applicable) selecting a target.
    """

    def __init__(self, options: Optional[List[Command]] = None) -> None:
        self.options: List[Command] = options or [
            Command.ATTACK,
            Command.SKILL,
            Command.ITEM,
            Command.DEFEND,
            Command.FLEE,
        ]
        if not self.options:
            raise ValueError("CommandMenu requires at least one command option")

        self.index: int = 0
        self.state: MenuState = MenuState.MENU
        self.selected_command: Optional[Command] = None
        self._targets: List[Target] = []
        self._target_index: int = 0
        self._result: Optional[SelectionResult] = None

    # --- Menu navigation ---

    def move_up(self) -> None:
        if self.state != MenuState.MENU:
            logger.debug("Ignored move_up: not in MENU state")
            return
        prev = self.index
        self.index = (self.index - 1) % len(self.options)
        logger.debug("Menu move_up: %s -> %s", prev, self.index)

    def move_down(self) -> None:
        if self.state != MenuState.MENU:
            logger.debug("Ignored move_down: not in MENU state")
            return
        prev = self.index
        self.index = (self.index + 1) % len(self.options)
        logger.debug("Menu move_down: %s -> %s", prev, self.index)

    # --- Target navigation ---

    def move_left(self) -> None:
        if self.state != MenuState.TARGET_SELECT or not self._targets:
            logger.debug("Ignored move_left: not in TARGET_SELECT or no targets")
            return
        prev = self._target_index
        # Move left to previous alive target (wrap)
        for _ in range(len(self._targets)):
            self._target_index = (self._target_index - 1) % len(self._targets)
            if self._targets[self._target_index].alive:
                break
        logger.debug("Target move_left: %s -> %s", prev, self._target_index)

    def move_right(self) -> None:
        if self.state != MenuState.TARGET_SELECT or not self._targets:
            logger.debug("Ignored move_right: not in TARGET_SELECT or no targets")
            return
        prev = self._target_index
        # Move right to next alive target (wrap)
        for _ in range(len(self._targets)):
            self._target_index = (self._target_index + 1) % len(self._targets)
            if self._targets[self._target_index].alive:
                break
        logger.debug("Target move_right: %s -> %s", prev, self._target_index)

    # --- Actions ---

    def confirm(self, targets: Optional[List[Target]] = None) -> Optional[SelectionResult]:
        """Confirm selection in the current state.

        - In MENU state: select command; either finish immediately or transition
          to TARGET_SELECT if the command requires a target (ATTACK, SKILL).
        - In TARGET_SELECT state: select current target and finish.
        - In COMPLETE: return the existing result.

        Args:
            targets: Required when confirming a command that needs targets.

        Returns:
            SelectionResult when selection completes; otherwise None if the
            state transitions to TARGET_SELECT and awaits a target.
        """
        if self.state == MenuState.COMPLETE:
            logger.debug("confirm called in COMPLETE; returning existing result")
            return self._result

        if self.state == MenuState.MENU:
            command = self.options[self.index]
            logger.debug("Menu confirm on command: %s", command)
            if command in REQUIRES_TARGET:
                provided = list(targets or [])
                alive_targets = [t for t in provided if t.alive]
                if not alive_targets:
                    raise ValueError("No valid targets available for this command")
                self.selected_command = command
                self._targets = alive_targets
                # Move cursor to the first alive target. If none, we would have raised.
                self._target_index = 0
                self.state = MenuState.TARGET_SELECT
                logger.debug(
                    "Transition to TARGET_SELECT with %d targets", len(alive_targets)
                )
                return None
            # Immediate resolution
            self._result = SelectionResult(command=command, target_id=None)
            self.state = MenuState.COMPLETE
            logger.debug("Menu selection complete: %s", self._result)
            return self._result

        if self.state == MenuState.TARGET_SELECT:
            target = self._targets[self._target_index]
            if not target.alive:
                # Defensive: shouldn't happen due to navigation filtering
                logger.warning("Selected target is not alive; ignoring confirm")
                return None
            if self.selected_command is None:
                logger.error("Invariant violated: selected_command is None in TARGET_SELECT")
                raise RuntimeError("No command selected but in target selection state")
            self._result = SelectionResult(
                command=self.selected_command, target_id=target.id
            )
            self.state = MenuState.COMPLETE
            logger.debug("Target selection complete: %s", self._result)
            return self._result

        # Should not reach here
        logger.error("Unknown state in confirm: %s", self.state)
        return None

    def cancel(self) -> bool:
        """Cancel the current selection step.

        - If in TARGET_SELECT, returns to MENU and clears command/targets.
        - If in MENU, does nothing and returns False.
        - If in COMPLETE, does nothing and returns False.
        """
        if self.state == MenuState.TARGET_SELECT:
            logger.debug("Cancel from TARGET_SELECT -> MENU")
            self.state = MenuState.MENU
            self.selected_command = None
            self._targets = []
            self._target_index = 0
            self._result = None
            return True
        logger.debug("Cancel ignored in state: %s", self.state)
        return False

    def reset(self) -> None:
        """Reset menu to initial state for a new selection."""
        logger.debug("Resetting CommandMenu state")
        self.index = 0
        self.state = MenuState.MENU
        self.selected_command = None
        self._targets = []
        self._target_index = 0
        self._result = None

    # --- Read-only properties ---

    @property
    def current_option(self) -> Command:
        return self.options[self.index]

    @property
    def targets(self) -> List[Target]:
        return list(self._targets)

    @property
    def target_index(self) -> int:
        return self._target_index

    @property
    def result(self) -> Optional[SelectionResult]:
        return self._result
