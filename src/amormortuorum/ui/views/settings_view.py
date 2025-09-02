from __future__ import annotations

import logging
from typing import Optional

from ...save_system import SaveManager
from ...settings import SettingsManager

try:
    import arcade  # type: ignore
except Exception:  # pragma: no cover
    arcade = None  # type: ignore

from ..widgets import Button, Toggle, Slider

log = logging.getLogger(__name__)


class SettingsView(arcade.View):  # pragma: no cover - UI rendering
    """Settings screen with audio/video/controls stubs and live application."""

    def __init__(self, settings_mgr: SettingsManager, save_mgr: SaveManager):
        super().__init__()
        self.settings_mgr = settings_mgr
        self.save_mgr = save_mgr
        self.tab = "Audio"
        self.back_btn: Optional[Button] = None
        self.tab_buttons: list[Button] = []
        # Widgets
        self.toggles: list[Toggle] = []
        self.sliders: list[Slider] = []
        self.control_buttons: list[Button] = []

    def on_show_view(self):
        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)
        self.settings_mgr.adapter.bind_window(self.window)
        self._build_ui()

    def _build_ui(self) -> None:
        self.tab_buttons = []
        cx = self.window.width / 2
        top = self.window.height - 80
        gap = 120

        def set_tab(name: str):
            def _inner():
                self.tab = name
                log.debug("Switched to tab: %s", name)
            return _inner

        self.tab_buttons.append(Button(cx - gap, top, 140, 36, "Audio", set_tab("Audio")))
        self.tab_buttons.append(Button(cx, top, 140, 36, "Video", set_tab("Video")))
        self.tab_buttons.append(Button(cx + gap, top, 140, 36, "Controls", set_tab("Controls")))
        self.back_btn = Button(100, 50, 120, 36, "Back", self._go_back, center=False)
        self._build_tab_ui()

    def _build_tab_ui(self) -> None:
        # Clear existing widgets
        self.toggles.clear()
        self.sliders.clear()
        self.control_buttons.clear()
        if self.tab == "Audio":
            s = self.settings_mgr.settings.audio
            self.toggles.append(Toggle(160, 380, "Muted", s.muted, lambda v: self.settings_mgr.set_audio(muted=v)))
            self.sliders.append(Slider(160, 330, 300, "Master Volume", s.master_volume, lambda v: self.settings_mgr.set_audio(master_volume=v)))
            self.sliders.append(Slider(160, 280, 300, "Music Volume", s.music_volume, lambda v: self.settings_mgr.set_audio(music_volume=v)))
            self.sliders.append(Slider(160, 230, 300, "SFX Volume", s.sfx_volume, lambda v: self.settings_mgr.set_audio(sfx_volume=v)))
        elif self.tab == "Video":
            v = self.settings_mgr.settings.video
            self.toggles.append(Toggle(160, 380, "Fullscreen", v.fullscreen, lambda val: self._on_fullscreen(val)))
            self.toggles.append(Toggle(160, 340, "VSync", v.vsync, lambda val: self._on_vsync(val)))
            # Resolution selection stub: cycle through a few presets via buttons
            presets = ["1280x720", "1600x900", "1920x1080"]
            current = v.resolution
            def make_set_res(res: str):
                return lambda: self._on_resolution(res)
            x = 160
            for res in presets:
                self.control_buttons.append(Button(x, 280, 140, 32, res + ("*" if res == current else ""), make_set_res(res)))
                x += 160
        else:  # Controls
            c = self.settings_mgr.settings.controls
            # Stubs: show current bindings (no remapping UI yet)
            y = 360
            for label, key in [("Move Up", c.move_up), ("Move Down", c.move_down), ("Move Left", c.move_left), ("Move Right", c.move_right), ("Action", c.action)]:
                self.control_buttons.append(Button(160, y, 260, 32, f"{label}: {key}", lambda: None, center=False))
                y -= 44

    def _on_fullscreen(self, val: bool) -> None:
        self.settings_mgr.set_video(fullscreen=val)

    def _on_vsync(self, val: bool) -> None:
        self.settings_mgr.set_video(vsync=val)

    def _on_resolution(self, res: str) -> None:
        self.settings_mgr.set_video(resolution=res)
        self._build_tab_ui()  # refresh button highlights

    def _go_back(self) -> None:
        from .main_menu import MainMenuView
        # Ensure main menu reflect the latest snapshot state
        self.window.show_view(MainMenuView(self.settings_mgr, self.save_mgr))

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text("Settings", self.window.width / 2, self.window.height - 40, arcade.color.WHITE, 28, anchor_x="center")
        for b in self.tab_buttons:
            b.draw()
        if self.tab == "Audio":
            for t in self.toggles:
                t.draw()
            for s in self.sliders:
                s.draw()
        elif self.tab == "Video":
            for t in self.toggles:
                t.draw()
            for b in self.control_buttons:
                b.draw()
        else:
            for b in self.control_buttons:
                b.draw()
        if self.back_btn:
            self.back_btn.draw()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if self.back_btn and self.back_btn.hit_test(x, y):
            self.back_btn.click()
            return
        for b in self.tab_buttons:
            if b.hit_test(x, y):
                b.click()
                self._build_tab_ui()
                return
        if self.tab == "Audio":
            for t in self.toggles:
                if t.hit_test(x, y):
                    t.click()
                    return
            for s in self.sliders:
                if s.hit_test(x, y):
                    s.on_drag(x)
                    return
        elif self.tab == "Video":
            for t in self.toggles:
                if t.hit_test(x, y):
                    t.click()
                    return
            for b in self.control_buttons:
                if b.hit_test(x, y):
                    b.click()
                    return
        else:
            # Controls tab: no interactions yet
            pass

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int):
        if self.tab == "Audio":
            for s in self.sliders:
                if s.hit_test(x, y):
                    s.on_drag(x)
