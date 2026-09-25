"""The game itself: pieces falling, locking, clearing. No drawing, no effects."""
from __future__ import annotations

from . import events as ev
from .bag import SevenBag
from .board import Board
from .scoring import Scoring
from .tetromino import PIECES, cells_at, spawn_column

SPAWNING = "spawning"
PLACING = "placing"
DROPPING = "dropping"
SETTLING = "settling"
CLEARING = "clearing"
FINISHED = "finished"

SETTLE_FRAMES = 2
CLEAR_FRAMES = 14
HOVER_ROWS = 2


class Game:
    def __init__(self, brain, rng, clock, board=None, speed=1.0):
        self.brain = brain
        self.rng = rng
        self.clock = clock
        self.speed = speed
        self.board = board or Board()
        self.scoring = Scoring()
        self.events = []
        self.start()

    def start(self):
        self.board.clear()
        self.bag = SevenBag(self.rng)
        self.scoring.reset()
        self.brain.reset(self.board.columns)
        self.hold = None
        self.pieces = 0
        self.frame = 0
        self.timer = 0
        self.started_at = self.clock.elapsed()
        self.name = None
        self.plan = []
        self.move = None
        self.ranked = []
        self.settled_cells = []
        self.clearing_rows = []
        self.dead_rows = 0
        self.danger = 0.0
        self.state = SPAWNING
        self.events.append(ev.GameStarted())

    def resize(self, columns, rows):
        self.board = self.board.resized(columns, rows)
        self.brain.reset(self.board.columns)
        self.plan = []
        self.clearing_rows = []
        self.settled_cells = []
        self.state = SPAWNING
        self.timer = 0

    @property
    def elapsed(self):
        return self.clock.since(self.started_at, self.frame)

    @property
    def cells(self):
        return cells_at(self.name, self.rotation, self.x, self.y)

    @property
    def ghost_row(self):
        return self.board.landing_row(self.name, self.rotation, self.x, self.y)

    @property
    def ready_rows(self):
        return self.brain.ready_rows(self.board)

    def drain_events(self):
        drained, self.events = self.events, []
        return drained

    def spawn(self):
        self.name = self.bag.take()
        self.rotation = 0
        self.x = spawn_column(self.name, self.board.columns)
        self.y = -2
        alternative = self.hold if self.hold else self.bag.peek(1)[0]
        move, ranked = self.brain.choose(self.board, self.name, alternative)
        self.ranked = ranked
        if move is None or self.board.collides(self.cells):
            return self.top_out()
        self.move = move
        self.plan = self._route(move)
        self.state = PLACING
        self.timer = 0
        self.pieces += 1

    def _route(self, move):
        if move.hold:
            name = move.name
            origin = spawn_column(name, self.board.columns)
            steps = ["hold"]
        else:
            name = self.name
            origin = self.x
            steps = []
        turns = ["turn"] * (move.rotation % len(PIECES[name]))
        shift = move.column - origin
        slides = ["right" if shift > 0 else "left"] * abs(shift)
        while turns or slides:
            if turns:
                steps.append(turns.pop())
            if slides:
                steps.append(slides.pop())
        return steps

    def swap_hold(self):
        if self.hold is None:
            self.hold, self.name = self.name, self.bag.take()
        else:
            self.hold, self.name = self.name, self.hold
        self.rotation = 0
        self.x = spawn_column(self.name, self.board.columns)
        self.events.append(ev.HoldSwapped(self.hold))

    def apply(self, step):
        if step == "hold":
            return self.swap_hold()
        if step == "turn":
            turned = (self.rotation + 1) % len(PIECES[self.name])
            for kick in (0, -1, 1, -2, 2):
                if not self.board.collides(cells_at(self.name, turned, self.x + kick, self.y)):
                    self.rotation, self.x = turned, self.x + kick
                    return
            return
        shift = -1 if step == "left" else 1
        if not self.board.collides(cells_at(self.name, self.rotation, self.x + shift, self.y)):
            self.x += shift

    def lock(self):
        self.settled_cells = self.board.place(self.name, self.rotation, self.x, self.y)
        rows = self.board.full_rows()
        self.events.append(ev.PieceLocked(self.name, self.settled_cells, len(rows)))
        if rows:
            self.clearing_rows = rows
            self.state = CLEARING
        else:
            self.scoring.break_combo()
            self.state = SETTLING
        self.timer = 0

    def resolve_clear(self):
        count = len(self.clearing_rows)
        self.board.collapse(self.clearing_rows)
        gain, promoted = self.scoring.register(count)
        if promoted:
            self.events.append(ev.LevelReached(self.scoring.level))
        self.events.append(ev.RowsCleared(count, gain, self.scoring.combo,
                                          self.scoring.back_to_back, self.board.is_empty))
        self.clearing_rows = []
        self.state = SPAWNING

    def top_out(self):
        self.state = FINISHED
        self.timer = 0
        self.dead_rows = 0
        self.events.append(ev.ToppedOut())

    def update(self):
        self.frame += 1
        self.timer += 1
        self._track_danger()
        state = self.state
        if state == SPAWNING:
            self.spawn()
        elif state == PLACING:
            self._place_step()
        elif state == DROPPING:
            self._drop_step()
        elif state == SETTLING:
            if self.timer == 1:
                self.events.append(ev.PieceSettled(self.name, self.settled_cells))
            elif self.timer >= SETTLE_FRAMES:
                self.state = SPAWNING
        elif state == CLEARING:
            if self.timer == 1:
                names = [[self.board.cells[r][c] for c in range(self.board.columns)]
                         for r in self.clearing_rows]
                self.events.append(ev.RowsIgnited(list(self.clearing_rows), names))
            elif self.timer >= max(6, int(CLEAR_FRAMES / self.speed)):
                self.resolve_clear()
        elif state == FINISHED:
            self._collapse_step()

    def _track_danger(self):
        peak = max(self.board.heights())
        target = max(0.0, (peak - self.board.rows * 0.6) / (self.board.rows * 0.3))
        self.danger += (min(1.0, target) - self.danger) * 0.12

    def _place_step(self):
        every = max(1, int(round(2 / self.speed)))
        if self.timer % every == 0:
            if self.plan:
                self.apply(self.plan.pop(0))
            else:
                self.target_y = self.ghost_row
                self.state = DROPPING
        if self.frame % max(2, int(6 / self.speed)) == 0 and self.y < HOVER_ROWS:
            if not self.board.collides(cells_at(self.name, self.rotation, self.x, self.y + 1)):
                self.y += 1

    def _drop_step(self):
        step = max(2, int(3 * self.speed))
        previous = self.y
        self.y = min(self.target_y, self.y + step)
        self.events.append(ev.PieceFell(self.name, self.cells, previous))
        if self.y >= self.target_y:
            self.lock()

    def _collapse_step(self):
        if self.timer % 2 == 0:
            self.dead_rows += 1
        if self.dead_rows > self.board.rows + 14:
            self.start()
