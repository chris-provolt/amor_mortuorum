from __future__ import annotations

from typing import List

from ..combat.log import PagedLogViewModel


class LogViewFormatter:
    """Formats log lines for on-screen display or UI widgets.

    This class can be extended to include rich coloring or markup codes if the UI supports it.
    For now, it simply prefixes turns and returns plain strings.
    """

    def __init__(self, view_model: PagedLogViewModel) -> None:
        self.vm = view_model

    def current_lines(self) -> List[str]:
        return self.vm.get_page_lines()

    def recent_lines(self, n: int = 5) -> List[str]:
        return self.vm.get_recent_lines(n)

    def toggle_history(self) -> None:
        self.vm.toggle_history_mode()

    def page_next(self) -> None:
        self.vm.next_page()

    def page_prev(self) -> None:
        self.vm.prev_page()

    def page_first(self) -> None:
        self.vm.go_to_first()

    def page_last(self) -> None:
        self.vm.go_to_last()
