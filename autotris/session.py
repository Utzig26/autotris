"""Owns the run: state, keys, theme changes and the frame loop."""
from __future__ import annotations

import hashlib
import random
import time

from .ai import Brain
from .clock import FixedStepClock, RealClock
from .core import events as ev
from .core.board import Board, clamp_size
from .core.game import Game
from .display import Canvas, Screen
from .display.screen import terminal_size
from .input import KeyReader, build, help_rows
from .theming import ThemeRegistry
from .theming.registry import SYSTEM_KEY
from .view import Layout, Renderer, largest_scale
from .view.effects import Effects
from .view.layout import CHROME_HEIGHT, GAP, LEFT_WIDTH, RIGHT_WIDTH
from .view.transitions import random_transition

FPS = 30
DESKTOP_POLL_FRAMES = 45
TOAST_FRAMES = 70
HOLD_FLASH_FRAMES = 8


class Session:
    def __init__(self, options):
        self.options = options
        self.rng = random.Random(options.seed)
        self.effects_rng = random.Random(options.seed + 7)
        self.registry = ThemeRegistry(options.only)
        self.brain = Brain(self.rng, options.iq)
        self.clock = FixedStepClock(FPS) if options.deterministic else RealClock()
        self.clock.start()
        board = Board(*options.board) if options.board else Board()
        self.game = Game(self.brain, self.rng, self.clock, board, options.speed)
        self.effects = Effects(self.effects_rng)
        self.renderer = Renderer(self.effects_rng)
        self.commands = build()
        self.zen = options.zen
        self.help_visible = False
        self.paused = False
        self.cycle = not options.theme
        self.follow = False
        self.autofill = options.fill
        self.toast = None
        self.transition = None
        self.scale_want = options.scale
        self.scale = max(1, options.scale or 1)
        self.max_scale = 1
        self.hold_flash = 0
        self.desktop_stamp = None
        key = self.registry.resolve(options.theme) if options.theme else self.registry.order[0]
        if key == SYSTEM_KEY:
            self.follow = True
        self.theme = self.registry.get(key)
        self.theme_index = self.registry.index_of(key)
        self.swap_at = self.clock.elapsed() + options.gallery

    @property
    def theme_count(self):
        return len(self.registry)

    def say(self, message, frames=TOAST_FRAMES):
        self.toast = [message, frames]

    def help_lines(self):
        return help_rows(self)

    def status_line(self, theme, layout):
        board = self.game.board
        line = "%s · %s · %.1fx · %dx%d@%d · h for help" % (
            theme.key.replace("om:", ""), self.game.brain.label, self.game.speed,
            board.columns, board.rows, layout.scale)
        return ("⟳ " + line) if self.cycle else line

    def handle(self, key):
        command = self.commands.get(key)
        if command:
            command.execute(self)

    def set_theme(self, key, message=None):
        theme = self.registry.get(key)
        if not theme:
            return
        self.theme = theme
        self.transition = random_transition(self.canvas, self.effects_rng)
        self.say(message or theme.name)

    def step_theme(self, step):
        self.theme_index = (self.theme_index + step) % len(self.registry)
        self.set_theme(self.registry.order[self.theme_index])

    def restart_cycle(self):
        self.swap_at = self.clock.elapsed() + self.options.gallery

    def watch_desktop(self):
        from .theming import omarchy
        self.desktop_stamp = omarchy.active_stamp()
        self.set_theme(SYSTEM_KEY, "following the desktop: %s" % (self.desktop_stamp[0] or "?"))

    def resize_blocks(self, step):
        target = (self.scale_want or self.scale) + step
        self.scale_want = max(1, min(self.max_scale, target))
        self.say("block size %d" % self.scale_want)
        if self.autofill:
            self.fill_window(announce=False)

    def set_board(self, columns, rows, announce=True, keep_fill=False):
        columns, rows = clamp_size(columns, rows)
        board = self.game.board
        if (columns, rows) != (board.columns, board.rows):
            self.game.resize(columns, rows)
        if not keep_fill:
            self.autofill = False
        if announce:
            self.say("board %dx%d" % (columns, rows))

    def fill_window(self, announce=True):
        canvas = self.canvas
        scale = max(1, self.scale)
        spare_width = 0 if self.zen else (LEFT_WIDTH + RIGHT_WIDTH + 2 * GAP)
        spare_height = 0 if self.zen else CHROME_HEIGHT
        columns = (canvas.width - spare_width - 2) // (2 * scale)
        rows = (canvas.height - spare_height - 2) // scale
        self.autofill = True
        self.set_board(columns, rows, announce=False, keep_fill=True)
        if announce:
            board = self.game.board
            self.say("filled the window: %dx%d" % (board.columns, board.rows))

    def refit(self):
        if self.autofill:
            self.fill_window(announce=False)

    def _measure(self):
        board = self.game.board
        self.max_scale = largest_scale(self.canvas.width, self.canvas.height, board, self.zen)
        self.scale = min(self.max_scale, self.scale_want or self.max_scale)
        self.layout = Layout(self.canvas.width, self.canvas.height, board, self.scale, self.zen)

    def _follow_desktop(self, frames):
        if not (self.follow and frames % DESKTOP_POLL_FRAMES == 0):
            return
        from .theming import omarchy
        stamp = omarchy.active_stamp()
        if stamp != self.desktop_stamp:
            self.desktop_stamp = stamp
            self.set_theme(SYSTEM_KEY, "desktop switched to %s" % (stamp[0] or "?"))

    def _advance_toast(self):
        if self.toast:
            self.toast[1] -= 1
            if self.toast[1] <= 0:
                self.toast = None

    def run(self, hooks=None):
        options = self.options
        width, height = terminal_size()
        self.canvas = Canvas(width, height)
        if self.autofill:
            self.fill_window(announce=False)
        self._measure()
        digest = hashlib.sha256() if options.digest else None
        frames = 0
        self.clock.start()
        with Screen(alternate=not options.no_alt) as screen, KeyReader() as keys:
            try:
                while True:
                    if hooks:
                        hooks.before(self, frames)
                    now = self.clock.elapsed()
                    for key in keys.pending():
                        self.handle(key)
                    if screen.take_resize():
                        self.canvas.resize(*terminal_size())
                        self.renderer.reseed()
                        self.transition = None
                        self.refit()
                    self._measure()
                    self._follow_desktop(frames)
                    if self.cycle and now >= self.swap_at:
                        self.swap_at = now + options.gallery
                        self.step_theme(1)
                    if not self.paused:
                        if self.hold_flash:
                            self.hold_flash -= 1
                        self.game.update()
                        events = self.game.drain_events()
                        for event in events:
                            if isinstance(event, ev.HoldSwapped):
                                self.hold_flash = HOLD_FLASH_FRAMES
                        self.effects.update(events, self.theme, self.layout, self.game)
                    self._advance_toast()
                    self.renderer.draw(self.canvas, self, now)
                    if self.transition:
                        self.transition.compose(self.canvas, self.theme)
                        if self.transition.done:
                            self.transition = None
                    if digest is not None:
                        digest.update(("".join("".join(r) for r in self.canvas.ch)).encode())
                        digest.update(repr(self.canvas.fg).encode())
                        digest.update(repr(self.canvas.bg).encode())
                    elif not options.plain:
                        screen.present(self.canvas)
                    if hooks:
                        hooks.after(self.canvas, frames)
                    frames += 1
                    self.clock.tick()
                    if options.frames and frames >= options.frames:
                        break
                    self.clock.pace(frames, FPS)
            except KeyboardInterrupt:
                pass
        if options.plain:
            print(self.canvas.to_text())
        if digest is not None:
            print(digest.hexdigest())
