from __future__ import annotations

from ...display.color import shade
from ..widget import Panel

WARMUP_SECONDS = 3


class StatsPanel(Panel):
    title = "STATS"
    height = 11

    def contents(self, canvas, scene):
        game, theme = scene.game, scene.theme
        scoring = game.scoring
        score = "{:,}".format(scoring.score).replace(",", " ")
        canvas.text(self.x + 2, self.y + 1, "SCORE", shade(theme.muted, 1.1))
        canvas.text(self.x + self.width - 2 - len(score), self.y + 2, score, theme.highlight)
        warm = game.elapsed > WARMUP_SECONDS
        rows = [
            ("LINES", str(scoring.lines)),
            ("LEVEL", str(scoring.level)),
            ("PIECES", str(game.pieces)),
            ("TETRIS", str(scoring.tetrises)),
            ("PPS", "%.2f" % (game.pieces / game.elapsed) if warm else "—"),
            ("LPM", "%.0f" % (scoring.lines * 60 / game.elapsed) if warm else "—"),
            ("TIME", "%02d:%02d" % (int(game.elapsed) // 60, int(game.elapsed) % 60)),
        ]
        for index, (label, value) in enumerate(rows):
            canvas.text(self.x + 2, self.y + 3 + index, label, theme.muted)
            canvas.text(self.x + self.width - 2 - len(value), self.y + 3 + index,
                        value, theme.foreground)
