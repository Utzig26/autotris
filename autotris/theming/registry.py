"""Everything selectable: built-in themes, Omarchy themes, and the live one."""
from __future__ import annotations

from . import frames, omarchy
from .backdrops import Gradient
from .blocks import SolidBlocks
from .builtin import BUILTIN
from .theme import Theme

OMARCHY_PREFIX = "om:"
SYSTEM_KEY = "system"


def _from_omarchy(key, data, name=None):
    return Theme(
        key=OMARCHY_PREFIX + key,
        name=(name or key).replace("-", " ").upper(),
        tagline="omarchy // %s // %s" % ("light" if data["light"] else "dark",
                                         data["accent_hex"] or "—"),
        palette=data["palette"],
        background_color=data["background_color"],
        horizon_color=data["horizon_color"],
        foreground=data["foreground"],
        muted=data["muted"],
        accent=data["accent"],
        highlight=data["highlight"],
        blocks=SolidBlocks(),
        backdrop=Gradient(),
        frame=frames.ROUND if data["light"] else frames.THIN,
        grid_dot="·",
        particles=("·", "•", "+"),
        light=data["light"],
        group="omarchy",
    )


class ThemeRegistry:
    def __init__(self, scope="all"):
        self.themes = {theme.key: theme for theme in BUILTIN}
        for name, path in omarchy.installed().items():
            try:
                theme = _from_omarchy(name, omarchy.palette(path))
            except (OSError, ValueError, KeyError):
                continue
            self.themes[theme.key] = theme
        self.order = self._ordered(scope)

    def _ordered(self, scope):
        builtin = [theme.key for theme in BUILTIN]
        omarchy_keys = sorted(k for k in self.themes if k.startswith(OMARCHY_PREFIX))
        if scope == "builtin":
            return builtin
        if scope == "omarchy":
            return omarchy_keys
        return builtin + omarchy_keys

    def __len__(self):
        return len(self.order)

    def __contains__(self, key):
        return key in self.themes

    def resolve(self, name):
        if not name:
            return self.order[0]
        if name in (SYSTEM_KEY, "desktop", "omarchy"):
            return SYSTEM_KEY
        if name in self.themes:
            return name
        prefixed = OMARCHY_PREFIX + name
        if prefixed in self.themes:
            return prefixed
        return self.order[0]

    def get(self, key):
        if key == SYSTEM_KEY:
            return self.system() or self.themes[self.order[0]]
        return self.themes.get(key)

    def system(self):
        current = omarchy.active_name()
        if not current:
            return None
        available = omarchy.installed()
        path = available.get(current)
        if not path:
            current = current.lower().replace(" ", "-")
            path = available.get(current)
        if not path:
            return None
        theme = _from_omarchy(current, omarchy.palette(path))
        theme.key = SYSTEM_KEY
        theme.name = current.replace("-", " ").upper()
        theme.tagline = "following your desktop theme"
        theme.group = "system"
        return theme

    def index_of(self, key):
        return self.order.index(key) if key in self.order else 0
