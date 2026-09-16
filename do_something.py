#!/usr/bin/env python3
"""Do Something — look extremely busy on every screen. Native Qt, no Chromium."""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "do-something"
APP_DISPLAY_NAME = "Do Something"
APP_VERSION = "0.1.0"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT = app_root()

BASE_HOSTS = [
    "gibson", "nexus-7", "busybox", "coffee-pot.local", "do-something",
    "shadow-gw", "printer-that-knows", "ice-wall", "mainframe", "not-reddit",
    "build-03", "k8s-node-12", "bastion", "gpu-box", "nas-under-desk",
]
BASE_FILES = [
    "src/main.rs", "kernel/sched.c", "do_something.py", "net/packet.rs",
    "ui/busy.js", "crypto/imaginary.c", "cmd/deploy.go", "lib/effort.py",
    "internal/something.go", "crates/busy/src/lib.rs", "Makefile",
]
BASE_PROCS = [
    "do-something --harder", "cargo build --release", "nvim src/main.rs",
    "chromium --app=definitely-work", "python3 looking_busy.py",
    "docker compose up", "node node_modules/.bin/webpack", "htop",
    "ssh gibson", "make -j$(nproc)", "rustc --edition 2021", "k9s",
    "ffmpeg -i meeting.mkv", "zsh", "pipewire",
]
BASE_CRATES = [
    "syn", "tokio", "serde", "anyhow", "thiserror", "clap", "regex",
    "hyper", "tracing", "axum", "reqwest", "hashbrown", "parking_lot",
]
BASE_GLYPHS = "01ABCDEF#$%&*+<>|/=アイウエオカキクケコサシス0123456789"
BASE_STATUSES = [
    "compiling something",
    "looking busy",
    "negotiating with the mainframe",
    "cargo build --release",
    "definitely working",
    "sudo do something --force",
    "waiting for tests that will pass",
    "syncing theatrical buffers",
    "productivity: not found",
    "deploying vibes to prod",
]
KINDS = [
    "term", "compile", "packets", "kernel", "hex", "code",
    "htop", "bars", "stats", "rain", "radar", "mesh", "cube",
]
SHAPES = {
    "cube": (
        [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
         (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
        [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
         (0, 4), (1, 5), (2, 6), (3, 7)],
    ),
    "tetra": (
        [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)],
        [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)],
    ),
    "octa": (
        [(1.2, 0, 0), (-1.2, 0, 0), (0, 1.2, 0), (0, -1.2, 0), (0, 0, 1.2), (0, 0, -1.2)],
        [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5),
         (2, 4), (2, 5), (3, 4), (3, 5)],
    ),
    "pyramid": (
        [(-1.1, -0.9, -1.1), (1.1, -0.9, -1.1), (1.1, -0.9, 1.1), (-1.1, -0.9, 1.1), (0, 1.3, 0)],
        [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)],
    ),
    "needle": (
        [(0, 1.6, 0), (0, -1.6, 0), (0.45, 0, 0), (-0.45, 0, 0), (0, 0, 0.45), (0, 0, -0.45)],
        [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5),
         (2, 4), (4, 3), (3, 5), (5, 2)],
    ),
}
SHAPE_NAMES = list(SHAPES.keys())


def pad(n: int, w: int = 2) -> str:
    return str(n).zfill(w)


def hx(n: int) -> str:
    return f"{n:02x}"


def _glow(h: float, s: float, l: float) -> QColor:
    r, g, b = colorsys.hls_to_rgb(h % 1.0, l, s)
    return QColor(int(r * 255), int(g * 255), int(b * 255))


@dataclass
class Palette:
    bg: QColor
    fg: QColor
    fg_dim: QColor
    accent: QColor
    warn: QColor
    alert: QColor
    mag: QColor
    panel: QColor

    @staticmethod
    def from_digest(d: bytes) -> "Palette":
        fg = _glow(d[0] / 255.0, 0.55 + d[1] / 255.0 * 0.4, 0.54 + d[2] / 255.0 * 0.16)
        accent = _glow(d[3] / 255.0, 0.50 + d[4] / 255.0 * 0.4, 0.56 + d[5] / 255.0 * 0.14)
        warn = _glow(d[6] / 255.0, 0.55 + d[7] / 255.0 * 0.35, 0.55 + d[8] / 255.0 * 0.14)
        mag = _glow(d[9] / 255.0, 0.50 + d[10] / 255.0 * 0.4, 0.55 + d[11] / 255.0 * 0.14)
        alert = _glow(d[12] / 255.0, 0.62 + d[13] / 255.0 * 0.3, 0.52 + d[14] / 255.0 * 0.12)
        bg = _glow(d[15] / 255.0, 0.25 + d[16] / 255.0 * 0.25, 0.028 + d[17] / 255.0 * 0.025)
        fg_dim = QColor(fg.red() // 3, fg.green() // 3, fg.blue() // 3)
        panel = QColor(min(255, bg.red() + 10), min(255, bg.green() + 14), min(255, bg.blue() + 10), 220)
        return Palette(bg=bg, fg=fg, fg_dim=fg_dim, accent=accent, warn=warn,
                       alert=alert, mag=mag, panel=panel)


class SeedWorld:
    """Phrase -> SHA-256 hex stream that scrambles the whole show."""

    def __init__(self, phrase: str):
        self.phrase = (phrase or "").strip() or "do something"
        self.digest = hashlib.sha256(self.phrase.encode("utf-8")).digest()
        self.hex = self.digest.hex()
        self.seed_int = int.from_bytes(self.digest[:4], "big") or 1
        tokens = [t for t in re.split(r"[^A-Za-z0-9]+", self.phrase) if t]
        self.tokens = tokens or ["something"]
        self.slug = "-".join(t.lower() for t in self.tokens)
        self.ident = "_".join(t.lower() for t in self.tokens)[:24] or "something"
        self.pal = Palette.from_digest(self.digest)
        self.shape = SHAPE_NAMES[self.digest[18] % len(SHAPE_NAMES)]
        self.shape2 = SHAPE_NAMES[self.digest[19] % len(SHAPE_NAMES)]
        self.ip_a = 10 + self.digest[8] % 214
        self.ip_b = self.digest[9]
        rot = self.digest[20] % len(BASE_GLYPHS)
        self.glyphs = (BASE_GLYPHS[rot:] + BASE_GLYPHS[:rot] + self.hex.upper())[:80]
        slug = self.slug
        ident = self.ident
        tok0 = self.tokens[0].lower()
        tok_last = self.tokens[-1].lower()
        self.hosts = [
            f"{slug}.local",
            f"{tok0}-gw",
            f"{tok_last}-node",
            f"node-{self.hex[:6]}",
            *BASE_HOSTS,
        ]
        self.files = [
            f"src/{ident}.rs",
            f"cmd/{tok0}.go",
            f"lib/{tok_last}.py",
            *BASE_FILES,
        ]
        self.procs = [
            f"./{ident} --seed",
            f"nvim src/{ident}.rs",
            f"ssh {slug}.local",
            *BASE_PROCS,
        ]
        self.crates = [ident[:12] or "seed", tok0, *BASE_CRATES]
        self.statuses = [
            f"running {self.phrase}",
            f"seed {self.hex[:8]}",
            f"checking {tok0}",
            f"warming {tok_last}",
            *BASE_STATUSES,
        ]
        self.titles = {
            "term": [f"root@{slug}:~", "journalctl -f", f"ssh {tok0}-gw"],
            "compile": [f"cargo test -p {ident[:16]}", "make -j32", "build.log"],
            "packets": [f"tcpdump -i {tok0}0", "wireshark · eth0"],
            "kernel": ["dmesg -w", "journalctl -k"],
            "hex": [f"hexdump -C /dev/{tok_last}", f"gdb -p {int(self.digest[21]) + 100}"],
            "code": [f"nvim src/{ident}.rs", f"{ident}.py"],
            "htop": ["htop"],
            "bars": [f"sudo {ident}", f"decrypt --{tok0}"],
            "stats": [self.phrase.upper()[:18] or "STATUS", "busyness.mon"],
            "rain": [f"tty{self.digest[22] % 9}", f"{tok0}.sys"],
            "radar": [f"radar://{slug}", f"k9s {tok0}"],
            "mesh": [f"nettop {tok_last}", "wireshark · eth0"],
            "cube": [f"{self.shape}.obj", f"glxgears --{tok0}"],
        }
        self.bar_labels = [
            f"{self.phrase} layer",
            f"decrypting {tok0}",
            f"{self.hex[:8]} handshake",
            f"compiling {tok_last}",
            f"mounting /dev/{slug[:12]}",
            f"looking busy ({tok0})",
        ]
        self.code = [
            [
                f"fn {ident}(ctx: &mut Ctx) -> Result<()> {{",
                f"    // seed {self.hex[:16]}",
                f"    let phrase = \"{self.phrase}\";",
                "    ctx.queue.steal().ok_or(Busy)?.decrypt(ctx.key)?;",
                f"    ctx.bus.emit(Event::{tok0.title().replace('-', '')});",
                "    Ok(())",
                "}",
            ],
            [
                f"def {ident}(target):",
                f"    seed = bytes.fromhex(\"{self.hex[:16]}\")",
                f"    for host in scan(\"{slug}\"):",
                f"        if host.open(22) and host.named(\"{tok0}\"):",
                f"            pivot(host, task={tok_last!r})",
                "    return Status.DEFINITELY_WORKING",
            ],
            [
                f"void *{ident}(ctx_t *ctx) {{",
                f"    /* {self.phrase} / {self.hex[:12]} */",
                "    packet_t *pkt = steal(&ctx->queue);",
                "    if (!pkt) return NULL;",
                "    decrypt(pkt->payload, pkt->len, ctx->key);",
                "    return pkt;",
                "}",
            ],
            [
                f"MOV RAX, [{tok0.upper()[:8]}]",
                f"MOV RDI, 0x{self.hex[:8]}",
                "SYSCALL",
                f"JNE still_{tok_last[:8]}",
                "RET",
            ],
        ]
        kinds = list(KINDS)
        rot_k = self.digest[23] % len(kinds)
        self.kinds = kinds[rot_k:] + kinds[:rot_k]

    def contact(self, i: int) -> str:
        tok = self.tokens[i % len(self.tokens)].upper()[:8]
        tag = self.hex[i * 2 : i * 2 + 4].upper()
        return f"{tok}-{tag}"


class Rng:
    def __init__(self, seed: int):
        self.s = (seed & 0xFFFFFFFF) or 1

    def __call__(self) -> float:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.s / 4294967296

    def pick(self, arr):
        return arr[int(self() * len(arr)) % len(arr)]

    def irand(self, a: int, b: int) -> int:
        return a + int(self() * (b - a + 1))


@dataclass
class Panel:
    kind: str
    rect: QRect
    title: str
    color: QColor
    anchor: bool = False
    lines: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class ScreensaverGuard(QObject):
    """Quit on real input, like a screensaver. Esc works immediately."""

    _MOVE_PX = 24
    _MODIFIERS = {
        Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
        Qt.Key.Key_AltGr, Qt.Key.Key_Super_L, Qt.Key.Key_Super_R,
        Qt.Key.Key_CapsLock, Qt.Key.Key_NumLock, Qt.Key.Key_ScrollLock,
    }

    def __init__(self, grace_s: float = 0.9, parent=None):
        super().__init__(parent)
        self.armed = False
        self.origin = None
        self._done = False
        QTimer.singleShot(int(grace_s * 1000), self._arm)

    def _arm(self) -> None:
        self.armed = True
        self.origin = None

    def _exit(self, reason: str) -> bool:
        if self._done:
            return True
        self._done = True
        print(f"do-something  exit ({reason})", flush=True)
        QApplication.quit()
        return True

    def eventFilter(self, obj, event) -> bool:
        if self._done:
            return False
        et = event.type()
        if et in (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride):
            key = event.key()
            auto = bool(event.isAutoRepeat()) if hasattr(event, "isAutoRepeat") else False
            if key == Qt.Key.Key_Escape and not auto:
                return self._exit("escape")
        if not self.armed:
            return False
        if et in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            pos = event.globalPosition() if hasattr(event, "globalPosition") else None
            if pos is None:
                return False
            if self.origin is None:
                self.origin = pos
                return False
            dx = pos.x() - self.origin.x()
            dy = pos.y() - self.origin.y()
            if dx * dx + dy * dy >= self._MOVE_PX * self._MOVE_PX:
                return self._exit(f"mouse moved {dx:.0f},{dy:.0f}")
            return False
        if et == QEvent.Type.MouseButtonPress:
            return self._exit("mouse click")
        if et == QEvent.Type.KeyPress:
            if event.isAutoRepeat() or event.key() in self._MODIFIERS:
                return False
            return self._exit(f"key {int(event.key())}")
        if et == QEvent.Type.Wheel:
            delta = event.angleDelta()
            if abs(delta.x()) + abs(delta.y()) < 80:
                return False
            return self._exit("wheel")
        return False


class SeedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Do Something")
        self.setModal(True)
        self.setFixedSize(560, 300)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("System Check")
        self.hex_lab = QLabel("")
        self.hint = QLabel("enter to start   ·   esc to abort")
        self.title = QLabel("DO SOMETHING")
        self.seed_lab = QLabel("SEED")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(10)
        lay.addWidget(self.title)
        lay.addWidget(self.seed_lab)
        lay.addWidget(self.edit)
        lay.addWidget(self.hex_lab)
        lay.addStretch(1)
        lay.addWidget(self.hint)
        self.edit.textChanged.connect(self._refresh)
        self.edit.returnPressed.connect(self.accept)
        self._refresh()
        self.edit.setFocus()

    def phrase(self) -> str:
        text = self.edit.text().strip()
        return text or (self.edit.placeholderText() or "do something")

    def _refresh(self) -> None:
        world = SeedWorld(self.edit.text().strip() or self.edit.placeholderText())
        pal = world.pal
        self.hex_lab.setText(world.hex)
        self.hex_lab.setWordWrap(True)
        css = f"""
            QDialog {{ background: {pal.bg.name()}; }}
            QLabel {{ color: {pal.fg.name()}; font-family: monospace; }}
            QLabel#unused {{ }}
            QLineEdit {{
                background: #000;
                color: {pal.accent.name()};
                border: 1px solid {pal.fg.name()};
                padding: 8px;
                font-family: monospace;
                font-size: 16px;
            }}
        """
        self.setStyleSheet(css)
        self.title.setStyleSheet(f"color:{pal.accent.name()}; font-size:18px; letter-spacing:4px;")
        self.seed_lab.setStyleSheet(f"color:{pal.warn.name()}; letter-spacing:3px;")
        self.hex_lab.setStyleSheet(f"color:{pal.fg_dim.name()}; font-size:11px;")
        self.hint.setStyleSheet(f"color:{pal.fg_dim.name()};")


class BusyView(QWidget):
    def __init__(self, world: SeedWorld, screen_name: str, portrait: bool, salt: int = 0):
        super().__init__()
        self.world = world
        self.pal = world.pal
        self.rng = Rng((world.seed_int + salt * 97) & 0xFFFFFFFF)
        self.screen_name = screen_name
        self.force_portrait = portrait
        self.shape_name = world.shape if salt % 2 == 0 else world.shape2
        self.panels: list[Panel] = []
        self.drops: list[float] = []
        self.threats = 40000 + (world.seed_int * 13) % 90000
        self.packets = self.rng.irand(80000, 400000)
        self.t0 = time.monotonic()
        self.boot_until = self.t0 + 1.7
        self.boot_lines: list[str] = []
        self.next_boot = self.t0
        self.next_spawn = self.t0 + 2.2
        self.next_status = 0.0
        self.status = f"seeding {world.phrase}"
        self.ticker = "  ·  ".join(self.packet_line() for _ in range(18))
        self.tick_x = 0.0
        self.ang = self.rng() * 6.28
        self.laid_out = False
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(f"background:{self.pal.bg.name()};")
        fam = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
        self.font = QFont(fam, 10)
        self.font_sm = QFont(fam, 9)
        self.font_big = QFont(fam, 20)
        self.font_hud = QFont(fam, 11)
        self.font_hud.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.on_tick)
        self.timer.start()
        self.boot_script = [
            "DO SOMETHING  v0.nothing",
            f"SEED  {world.phrase}",
            f"HEX   {world.hex[:48]}",
            f"node  {screen_name}   shape {self.shape_name}",
            "",
            f"> mounting /dev/{world.slug[:16]}",
            "> loading busyness kernel ........... ok",
            "> scanning for actual work .......... none found",
            "> enabling theatrical protocols",
            "> covering display surface",
            f"> STATUS: {world.phrase}",
            "",
            "ready.",
        ]

    def portrait(self) -> bool:
        return self.force_portrait or self.height() > self.width()

    def skin(self, kind: str) -> QColor:
        return {
            "compile": self.pal.warn,
            "packets": self.pal.accent,
            "hex": self.pal.accent,
            "code": self.pal.warn,
            "bars": self.pal.mag,
            "stats": self.pal.accent,
            "mesh": self.pal.accent,
            "cube": self.pal.accent,
            "radar": self.pal.fg,
        }.get(kind, self.pal.fg)

    def ip(self) -> str:
        w = self.world
        return f"{w.ip_a}.{w.ip_b}.{self.rng.irand(0, 255)}.{self.rng.irand(1, 254)}"

    def hex32(self) -> str:
        return "".join(hx(self.rng.irand(0, 255)) for _ in range(8))

    def compile_line(self) -> str:
        r = self.rng
        w = self.world
        roll = r()
        if roll < 0.35:
            return f"   Compiling {r.pick(w.crates)} v1.{r.irand(0, 40)}.{r.irand(0, 12)}"
        if roll < 0.5:
            return f"    Finished `release` profile [optimized] in {r.irand(2, 58)}.{r.irand(10, 99)}s"
        if roll < 0.65:
            return f"[{pad(r.irand(1, 99))}%] Building CXX object {r.pick(w.files)}.o"
        if roll < 0.8:
            return f"ok  {r.pick(w.files)}  {r.irand(0, 2)}.{r.irand(10, 99)}s"
        return f"warning: unused variable `{w.ident}` in {r.pick(w.files)}"

    def sys_line(self) -> str:
        r = self.rng
        w = self.world
        h = r.pick(w.hosts)
        roll = r()
        if roll < 0.2:
            return f"[OK] ssh {h}  session {self.hex32()[:8]}"
        if roll < 0.4:
            return f"probe {self.ip()}:443  open  tls1.3  {r.pick(['h2', 'http/1.1'])}"
        if roll < 0.55:
            return f"k8s  pod/{h}  Ready  restarts={r.irand(0, 3)}"
        if roll < 0.7:
            return f"git  {r.pick(['fetch', 'rebase', 'push --force-with-lease', 'commit -m wip'])}  {self.hex32()[:7]}"
        if roll < 0.85:
            return f"docker  pulling {h}/{w.slug}:latest  {r.irand(10, 99)}MB"
        return f"[warn] {r.pick(w.files)}:{r.irand(10, 400)}  this looks like {w.tokens[0].lower()}"

    def packet_line(self) -> str:
        r = self.rng
        flags = r.pick(["S", "S.", "P.", ".", "F.", "R"])
        port = r.pick([22, 80, 443, 53, 51820, 1337, 7 + self.world.digest[24]])
        return (
            f"{pad(r.irand(0, 23))}:{pad(r.irand(0, 59))}:{pad(r.irand(0, 59))}.{r.irand(100, 999)}  "
            f"{self.ip()}.{port} > {self.ip()}.{r.irand(1024, 65535)}: Flags [{flags}], len {r.irand(40, 1400)}"
        )

    def hex_line(self, off: int) -> str:
        r = self.rng
        xor = self.world.digest
        raw = [(r.irand(0, 255) ^ xor[i % 32]) for i in range(16)]
        hxpart = " ".join(hx(b) for b in raw)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in raw)
        return f"{off:08x}  {hxpart}  |{asc}|"

    def kernel_line(self) -> str:
        r = self.rng
        w = self.world
        return r.pick(
            [
                f"usb 1-2: new SuperSpeed device ({w.slug})",
                f"nvidia  GPU0  sm {r.irand(40, 99)}%  mem {r.irand(20, 90)}%",
                f"wlan0: associated {self.hex32()[:12]}",
                f'audit: apparmor="ALLOWED" comm="{w.ident}"',
                f"EXT4-fs: mounted /dev/{w.slug[:12]} r/w",
                f"cpu{r.irand(0, 31)}: turbo enabled",
                f"pipewire: dummy sink '{w.tokens[0].lower()}' running",
            ]
        )

    def make_panel(self, kind: str, rect: QRect, anchor: bool = False) -> Panel:
        w = self.world
        title = self.rng.pick(w.titles.get(kind, w.titles["term"]))
        p = Panel(kind=kind, rect=rect, title=title, color=self.skin(kind), anchor=anchor)
        if kind == "hex":
            p.extra["off"] = self.rng.irand(0x1000, 0x80000)
        elif kind == "code":
            p.extra["blocks"] = [f"// {w.phrase}"] + list(self.rng.pick(w.code))
            p.extra["i"] = 0
            p.extra["col"] = 0
        elif kind == "htop":
            p.extra["rows"] = [
                {
                    "pid": self.rng.irand(100, 4000),
                    "cpu": self.rng() * 90,
                    "mem": self.rng() * 40,
                    "cmd": self.rng.pick(w.procs),
                }
                for _ in range(12)
            ]
        elif kind == "bars":
            p.extra["rows"] = [
                {"label": lab, "v": self.rng() * 70, "spd": 8 + self.rng() * 22}
                for lab in w.bar_labels
            ]
        elif kind == "radar":
            p.extra["blips"] = [
                {
                    "a": self.rng() * 6.28,
                    "r": 0.2 + self.rng() * 0.7,
                    "life": self.rng(),
                    "name": w.contact(i),
                }
                for i in range(8)
            ]
        elif kind == "mesh":
            ww, hh = max(40, rect.width()), max(40, rect.height())
            n = 12 + self.rng.irand(0, 6)
            nodes = [
                {
                    "x": 16 + self.rng() * (ww - 32),
                    "y": 16 + self.rng() * (hh - 32),
                    "vx": (self.rng() - 0.5) * 18,
                    "vy": (self.rng() - 0.5) * 18,
                }
                for _ in range(n)
            ]
            edges = []
            for i in range(n):
                for j in range(i + 1, n):
                    if self.rng() < 0.18:
                        edges.append((i, j))
            p.extra["nodes"] = nodes
            p.extra["edges"] = edges
            p.extra["pkts"] = []
        elif kind == "cube":
            p.extra["a"] = self.rng() * 4
            p.extra["b"] = self.rng() * 4
            p.extra["shape"] = self.shape_name
        elif kind == "rain":
            p.extra["drops"] = []
        elif kind == "stats":
            p.extra["packets"] = self.rng.irand(80000, 400000)
        gen = {
            "term": self.sys_line,
            "compile": self.compile_line,
            "packets": self.packet_line,
            "kernel": self.kernel_line,
        }.get(kind)
        if gen:
            for _ in range(10):
                p.lines.append(gen())
        return p

    def layout_anchors(self) -> None:
        self.panels = [p for p in self.panels if not p.anchor]
        w, h = self.width(), self.height()
        stage = QRect(8, 36, max(40, w - 16), max(40, h - 70))
        if self.portrait():
            cells = [
                (0.01, 0.01, 0.98, 0.24),
                (0.01, 0.26, 0.98, 0.20),
                (0.01, 0.47, 0.98, 0.22),
                (0.01, 0.70, 0.98, 0.28),
            ]
        else:
            cells = [
                (0.005, 0.01, 0.33, 0.52),
                (0.34, 0.01, 0.38, 0.36),
                (0.73, 0.01, 0.26, 0.34),
                (0.34, 0.39, 0.38, 0.30),
                (0.73, 0.37, 0.26, 0.34),
                (0.005, 0.55, 0.33, 0.43),
                (0.34, 0.71, 0.40, 0.27),
                (0.75, 0.73, 0.24, 0.25),
            ]
        bag = list(self.world.kinds)
        bag.sort(key=lambda _: self.rng())
        for i, c in enumerate(cells):
            kind = bag[i % len(bag)]
            rect = QRect(
                int(stage.x() + c[0] * stage.width()),
                int(stage.y() + c[1] * stage.height()),
                int(c[2] * stage.width()),
                int(c[3] * stage.height()),
            )
            self.panels.insert(i, self.make_panel(kind, rect, anchor=True))
        self.laid_out = True

    def spawn_overlay(self) -> None:
        w, h = self.width(), self.height()
        stage = QRect(8, 36, max(40, w - 16), max(40, h - 70))
        if self.portrait():
            pw, ph = min(520, stage.width() - 12), self.rng.irand(180, 320)
            cap = 14
        else:
            pw, ph = self.rng.pick([(520, 260), (640, 320), (380, 400), (700, 200)])
            cap = 13
        x = stage.x() + self.rng.irand(0, max(1, stage.width() - pw))
        y = stage.y() + self.rng.irand(0, max(1, stage.height() - ph))
        overlays = [p for p in self.panels if not p.anchor]
        if len(self.panels) >= cap and overlays:
            self.panels.remove(overlays[0])
        self.panels.append(
            self.make_panel(self.rng.pick(self.world.kinds), QRect(x, y, pw, ph), anchor=False)
        )

    def max_lines(self, rect: QRect) -> int:
        return max(4, (rect.height() - 30) // 14)

    def push_line(self, panel: Panel, line: str) -> None:
        panel.lines.append(line)
        cap = self.max_lines(panel.rect)
        if len(panel.lines) > cap:
            panel.lines = panel.lines[-cap:]

    def tick_panel(self, panel: Panel, dt: float) -> None:
        kind = panel.kind
        r = self.rng
        if kind == "term":
            if r() < 0.55:
                self.push_line(panel, self.sys_line())
        elif kind == "compile":
            if r() < 0.45:
                self.push_line(panel, self.compile_line())
        elif kind == "packets":
            if r() < 0.7:
                self.push_line(panel, self.packet_line())
        elif kind == "kernel":
            if r() < 0.35:
                self.push_line(panel, self.kernel_line())
        elif kind == "hex":
            if r() < 0.6:
                off = int(panel.extra.get("off", 0))
                self.push_line(panel, self.hex_line(off))
                panel.extra["off"] = off + 16
        elif kind == "code":
            blocks = panel.extra["blocks"]
            i = panel.extra["i"]
            col = panel.extra["col"]
            steps = max(1, int(dt * 42))
            for _ in range(steps):
                if i >= len(blocks):
                    blocks.extend([""] + list(r.pick(self.world.code)))
                    if len(blocks) > 48:
                        blocks[:] = blocks[-28:]
                        i = max(0, len(blocks) - 10)
                        col = 0
                line = blocks[i] if i < len(blocks) else ""
                col += 1
                if col > len(line):
                    i += 1
                    col = 0
            panel.extra["i"] = i
            panel.extra["col"] = col
            done = blocks[:i]
            cur = (blocks[i][:col] + "█") if i < len(blocks) else ""
            panel.lines = (done + [cur])[-self.max_lines(panel.rect) :]
        elif kind == "htop":
            for row in panel.extra["rows"]:
                row["cpu"] = min(99.9, max(0.1, row["cpu"] + (r() - 0.48) * 8))
                row["mem"] = min(70.0, max(0.2, row["mem"] + (r() - 0.5) * 2))
        elif kind == "bars":
            for row in panel.extra["rows"]:
                row["v"] += dt * row["spd"]
                if row["v"] > 99.2:
                    row["v"] = r() * 30
        elif kind == "stats":
            panel.extra["packets"] = int(panel.extra["packets"]) + r.irand(40, 400)
        elif kind == "radar":
            for b in panel.extra["blips"]:
                b["life"] += dt * 0.4
        elif kind == "mesh":
            nodes = panel.extra["nodes"]
            rw, rh = max(8, panel.rect.width() - 8), max(8, panel.rect.height() - 28)
            for n in nodes:
                n["x"] += n["vx"] * dt
                n["y"] += n["vy"] * dt
                if n["x"] < 8 or n["x"] > rw:
                    n["vx"] *= -1
                if n["y"] < 8 or n["y"] > rh:
                    n["vy"] *= -1
            if r() < 0.1 and panel.extra["edges"]:
                panel.extra["pkts"].append({"e": r.pick(panel.extra["edges"]), "t": 0.0})
            pkts = []
            for pkt in panel.extra["pkts"]:
                pkt["t"] += dt * 0.9
                if pkt["t"] < 1:
                    pkts.append(pkt)
            panel.extra["pkts"] = pkts
        elif kind == "cube":
            panel.extra["a"] += dt * 0.7
            panel.extra["b"] += dt * 0.95
        elif kind == "rain":
            drops = panel.extra["drops"]
            cols = max(4, panel.rect.width() // 12)
            while len(drops) < cols:
                drops.append(r() * panel.rect.height())
            for i in range(len(drops)):
                drops[i] += 12 + (i % 6)
                if drops[i] > panel.rect.height() and r() > 0.96:
                    drops[i] = 0

    def on_tick(self) -> None:
        now = time.monotonic()
        dt = 0.05
        if now >= self.boot_until and not self.laid_out and self.width() > 40:
            self.layout_anchors()
        if now < self.boot_until:
            if now >= self.next_boot and len(self.boot_lines) < len(self.boot_script):
                self.boot_lines.append(self.boot_script[len(self.boot_lines)])
                self.next_boot = now + 0.11
        else:
            for panel in self.panels:
                self.tick_panel(panel, dt)
            if now >= self.next_spawn:
                self.spawn_overlay()
                self.next_spawn = now + 1.35
            if now >= self.next_status:
                self.status = self.rng.pick(self.world.statuses)
                self.next_status = now + 1.6
        self.threats += self.rng.irand(1, 17)
        self.packets += self.rng.irand(20, 120)
        self.tick_x += 80 * dt
        self.ang += dt * 1.8
        cols = max(8, self.width() // 12)
        while len(self.drops) < cols:
            self.drops.append(self.rng() * self.height())
        if len(self.drops) > cols:
            self.drops = self.drops[:cols]
        for i in range(len(self.drops)):
            self.drops[i] += 11 + (i % 6)
            if self.drops[i] > self.height() and self.rng() > 0.97:
                self.drops[i] = 0
        self.update()

    def paintEvent(self, event) -> None:
        pal = self.pal
        glyphs = self.world.glyphs
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), pal.bg)
        p.setFont(self.font_sm)
        for i, y in enumerate(self.drops):
            p.setPen(pal.fg if i % 5 == 0 else pal.fg_dim)
            ch = glyphs[(i * 7 + int(y)) % len(glyphs)]
            p.drawText(i * 12, int(y), ch)
        if time.monotonic() < self.boot_until or (
            not self.laid_out and time.monotonic() < self.t0 + 2.5
        ):
            self.paint_boot(p)
        else:
            for panel in self.panels:
                self.paint_panel(p, panel)
        self.paint_hud(p)
        self.paint_ticker(p)
        p.setPen(QPen(QColor(0, 0, 0, 50), 1))
        for y in range(0, self.height(), 3):
            p.drawLine(0, y, self.width(), y)
        p.fillRect(0, 0, self.width(), 8, QColor(0, 0, 0, 80))
        p.end()

    def paint_boot(self, p: QPainter) -> None:
        p.setFont(self.font_hud)
        p.setPen(self.pal.fg)
        y = self.height() // 2 - 110
        x = max(24, self.width() // 2 - 280)
        for i, line in enumerate(self.boot_lines):
            p.drawText(x, y + i * 22, line)
        if int(time.monotonic() * 4) % 2 == 0:
            p.drawText(x, y + len(self.boot_lines) * 22, "█")

    def paint_hud(self, p: QPainter) -> None:
        pal = self.pal
        p.fillRect(0, 0, self.width(), 32, QColor(0, 0, 0, 160))
        p.setFont(self.font_hud)
        p.setPen(pal.accent)
        p.drawText(14, 22, "DO SOMETHING")
        now = time.localtime()
        clock = f"{pad(now.tm_hour)}:{pad(now.tm_min)}:{pad(now.tm_sec)}"
        right = f"{self.world.hex[:8]}  {clock}  {self.threats}"
        p.setPen(pal.warn)
        p.drawText(
            QRect(0, 0, self.width() - 16, 32),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            right,
        )
        p.setPen(pal.fg)
        p.drawText(
            QRect(170, 0, max(80, self.width() - 430), 32),
            Qt.AlignmentFlag.AlignVCenter,
            self.status.upper(),
        )
        p.setPen(QColor(pal.fg.red(), pal.fg.green(), pal.fg.blue(), 90))
        p.setFont(self.font_sm)
        p.drawText(
            QRect(0, self.height() - 58, self.width(), 20),
            Qt.AlignmentFlag.AlignHCenter,
            "move the mouse or press a key",
        )

    def paint_ticker(self, p: QPainter) -> None:
        pal = self.pal
        h = 26
        y = self.height() - h
        p.fillRect(0, y, self.width(), h, QColor(0, 0, 0, 180))
        p.setPen(QColor(pal.fg.red(), pal.fg.green(), pal.fg.blue(), 50))
        p.drawLine(0, y, self.width(), y)
        p.setFont(self.font_sm)
        p.setPen(pal.accent)
        text = self.ticker + "   ·   " + self.ticker
        x = -int(self.tick_x) % (len(self.ticker) * 7 + 80)
        p.drawText(10 - x, y + 18, text)

    def paint_panel(self, p: QPainter, panel: Panel) -> None:
        pal = self.pal
        r = panel.rect
        if r.width() < 20 or r.height() < 20:
            return
        p.fillRect(r, pal.panel)
        p.setPen(QPen(panel.color, 1))
        p.drawRect(r.adjusted(0, 0, -1, -1))
        p.fillRect(QRect(r.x(), r.y(), r.width(), 22), QColor(0, 0, 0, 150))
        p.setPen(QPen(panel.color.darker(160), 1))
        p.drawLine(r.x(), r.y() + 22, r.right(), r.y() + 22)
        p.setFont(self.font_sm)
        p.setPen(pal.alert)
        p.drawText(r.x() + 8, r.y() + 16, "●")
        p.setPen(pal.warn)
        p.drawText(r.x() + 20, r.y() + 16, "●")
        p.setPen(pal.fg)
        p.drawText(r.x() + 32, r.y() + 16, "●")
        p.setPen(pal.fg)
        p.drawText(r.x() + 48, r.y() + 16, panel.title)
        p.setPen(pal.alert)
        p.drawText(r.right() - 16, r.y() + 16, "●")
        body = r.adjusted(6, 26, -6, -6)
        p.save()
        p.setClipRect(body)
        kind = panel.kind
        if kind in ("term", "compile", "packets", "kernel", "hex", "code"):
            p.setFont(self.font_sm)
            p.setPen(panel.color if kind != "term" else pal.fg)
            for i, line in enumerate(panel.lines):
                p.drawText(body.x(), body.y() + 12 + i * 14, line)
        elif kind == "htop":
            self.paint_htop(p, panel, body)
        elif kind == "bars":
            self.paint_bars(p, panel, body)
        elif kind == "stats":
            self.paint_stats(p, panel, body)
        elif kind == "rain":
            self.paint_mini_rain(p, panel, body)
        elif kind == "radar":
            self.paint_radar(p, panel, body)
        elif kind == "mesh":
            self.paint_mesh(p, panel, body)
        elif kind == "cube":
            self.paint_shape(p, panel, body)
        p.restore()

    def paint_htop(self, p: QPainter, panel: Panel, body: QRect) -> None:
        r = self.rng
        rows = sorted(panel.extra["rows"], key=lambda x: -x["cpu"])[:9]
        load = f"{1.2 + r() * 8:.2f}"
        cpu = r.irand(60, 99)
        mem = r.irand(20, 70)
        lines = [
            f"Tasks: {r.irand(180, 420)} total, {r.irand(2, 9)} running   load {load}",
            f"CPU [{'#' * (cpu // 5):.<24}]  {cpu}%",
            f"Mem [{'#' * (mem // 5):.<24}]  {mem}%",
            "  PID  CPU%  MEM%  COMMAND",
        ]
        for row in rows:
            lines.append(
                f"{row['pid']:>5}  {row['cpu']:4.1f}  {row['mem']:4.1f}  {row['cmd']}"
            )
        p.setFont(self.font_sm)
        p.setPen(self.pal.fg)
        for i, line in enumerate(lines):
            p.drawText(body.x(), body.y() + 12 + i * 14, line)

    def paint_bars(self, p: QPainter, panel: Panel, body: QRect) -> None:
        pal = self.pal
        p.setFont(self.font_sm)
        for i, row in enumerate(panel.extra["rows"]):
            y = body.y() + i * 22
            p.setPen(pal.mag)
            p.drawText(body.x(), y + 12, row["label"][:22])
            bar = QRect(body.x() + 168, y + 4, max(20, body.width() - 210), 10)
            p.fillRect(bar, QColor(10, 26, 16))
            p.setPen(QColor(pal.fg.red(), pal.fg.green(), pal.fg.blue(), 60))
            p.drawRect(bar)
            fill = QRect(bar.x(), bar.y(), int(bar.width() * (row["v"] / 100.0)), bar.height())
            p.fillRect(fill, pal.fg)
            p.setPen(pal.fg)
            p.drawText(bar.right() + 8, y + 12, f"{int(row['v'])}%")

    def paint_stats(self, p: QPainter, panel: Panel, body: QRect) -> None:
        pal = self.pal
        up = int(time.monotonic() - self.t0)
        cells = [
            ("PACKETS", f"{int(panel.extra['packets']):,}"),
            ("SEED", self.world.hex[:8].upper()),
            ("UPTIME", f"{up // 60:02d}:{up % 60:02d}"),
            ("STATUS", "BUSY"),
        ]
        cols, rows_n = 2, 2
        cw, ch = body.width() // cols, body.height() // rows_n
        for i, (k, v) in enumerate(cells):
            x = body.x() + (i % cols) * cw
            y = body.y() + (i // cols) * ch
            box = QRect(x + 3, y + 3, cw - 6, ch - 6)
            p.setPen(QColor(pal.fg.red(), pal.fg.green(), pal.fg.blue(), 50))
            p.drawRect(box)
            p.setFont(self.font_sm)
            p.setPen(QColor(pal.fg.red(), pal.fg.green(), pal.fg.blue(), 140))
            p.drawText(box.adjusted(8, 6, 0, 0), k)
            p.setFont(self.font_big)
            p.setPen(pal.accent)
            p.drawText(box.adjusted(8, 22, -8, -4), Qt.AlignmentFlag.AlignVCenter, v)

    def paint_mini_rain(self, p: QPainter, panel: Panel, body: QRect) -> None:
        drops = panel.extra["drops"]
        glyphs = self.world.glyphs
        pal = self.pal
        p.setFont(self.font_sm)
        for i, y in enumerate(drops):
            p.setPen(pal.fg if i % 4 == 0 else pal.fg_dim)
            ch = glyphs[(i * 5 + int(y)) % len(glyphs)]
            p.drawText(body.x() + i * 12, body.y() + int(y) % max(12, body.height()), ch)

    def paint_radar(self, p: QPainter, panel: Panel, body: QRect) -> None:
        pal = self.pal
        cx = body.center().x()
        cy = body.center().y()
        rad = min(body.width(), body.height()) * 0.38
        p.setPen(QPen(QColor(pal.fg.red(), pal.fg.green(), pal.fg.blue(), 90), 1))
        for i in range(1, 5):
            p.drawEllipse(QPointF(cx, cy), rad * i / 4, rad * i / 4)
        p.drawLine(int(cx - rad), cy, int(cx + rad), cy)
        p.drawLine(cx, int(cy - rad), cx, int(cy + rad))
        path = QPainterPath()
        path.moveTo(cx, cy)
        path.arcTo(cx - rad, cy - rad, rad * 2, rad * 2, -math.degrees(self.ang), -32)
        path.closeSubpath()
        sweep = QColor(pal.fg.red(), pal.fg.green(), pal.fg.blue(), 40)
        p.fillPath(path, sweep)
        p.setPen(QPen(pal.fg, 1.5))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(self.ang) * rad, cy + math.sin(self.ang) * rad),
        )
        p.setFont(self.font_sm)
        for b in panel.extra["blips"]:
            alpha = int(80 + 150 * abs(math.sin(b["life"] * 4)))
            px = cx + math.cos(b["a"]) * rad * b["r"]
            py = cy + math.sin(b["a"]) * rad * b["r"]
            p.setPen(Qt.PenStyle.NoPen)
            col = QColor(pal.accent.red(), pal.accent.green(), pal.accent.blue(), alpha)
            p.setBrush(col)
            p.drawEllipse(QPointF(px, py), 3, 3)
            p.setPen(pal.accent)
            p.drawText(int(px) + 6, int(py) - 2, b.get("name", ""))
        p.setBrush(Qt.BrushStyle.NoBrush)

    def paint_mesh(self, p: QPainter, panel: Panel, body: QRect) -> None:
        pal = self.pal
        nodes = panel.extra["nodes"]
        p.setPen(QPen(QColor(pal.accent.red(), pal.accent.green(), pal.accent.blue(), 70), 1))
        for a, b in panel.extra["edges"]:
            p.drawLine(
                QPointF(body.x() + nodes[a]["x"], body.y() + nodes[a]["y"]),
                QPointF(body.x() + nodes[b]["x"], body.y() + nodes[b]["y"]),
            )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.fg)
        for pkt in panel.extra["pkts"]:
            ia, ib = pkt["e"]
            t = pkt["t"]
            x = nodes[ia]["x"] + (nodes[ib]["x"] - nodes[ia]["x"]) * t
            y = nodes[ia]["y"] + (nodes[ib]["y"] - nodes[ia]["y"]) * t
            p.drawEllipse(QPointF(body.x() + x, body.y() + y), 2.5, 2.5)
        p.setBrush(pal.accent)
        for n in nodes:
            p.drawEllipse(QPointF(body.x() + n["x"], body.y() + n["y"]), 3, 3)
        p.setBrush(Qt.BrushStyle.NoBrush)

    def paint_shape(self, p: QPainter, panel: Panel, body: QRect) -> None:
        pal = self.pal
        a = panel.extra["a"]
        b = panel.extra["b"]
        name = panel.extra.get("shape", self.shape_name)
        verts, edges = SHAPES.get(name, SHAPES["cube"])

        def rot(v):
            x, y, z = v
            y1 = y * math.cos(a) - z * math.sin(a)
            z1 = y * math.sin(a) + z * math.cos(a)
            x1 = x * math.cos(b) + z1 * math.sin(b)
            z2 = -x * math.sin(b) + z1 * math.cos(b)
            return x1, y1, z2

        s = min(body.width(), body.height()) * 0.28
        cx, cy = body.center().x(), body.center().y()
        pts = []
        for v in verts:
            x, y, z = rot(v)
            f = 2.4 / (3 + z)
            pts.append(QPointF(cx + x * s * f, cy + y * s * f))
        p.setPen(QPen(pal.accent, 1.4))
        for i, j in edges:
            p.drawLine(pts[i], pts[j])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.fg)
        for pt in pts:
            p.drawRect(int(pt.x()) - 2, int(pt.y()) - 2, 4, 4)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pal.fg_dim)
        p.setFont(self.font_sm)
        p.drawText(body.x() + 6, body.bottom() - 4, name)


class CoverWindow(BusyView):
    def __init__(self, screen, world: SeedWorld, salt: int):
        geo = screen.geometry()
        super().__init__(world, screen.name() or "display", geo.height() > geo.width(), salt)
        self.screen_ref = screen
        self.setWindowTitle("Do Something")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        for seq in ("Esc", "Q", "F11", "Ctrl+C"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(QApplication.quit)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        QApplication.quit()

    def place(self) -> None:
        screen = self.screen_ref
        geo = screen.geometry()
        self.setGeometry(geo)
        if sys.platform == "win32":
            self.showFullScreen()
            handle = self.windowHandle()
            if handle is not None:
                handle.setScreen(screen)
            self.raise_()
            self.activateWindow()
            self._win32_topmost()
        elif sys.platform == "darwin":
            self.setGeometry(geo)
            self.show()
            handle = self.windowHandle()
            if handle is not None:
                handle.setScreen(screen)
            self.setGeometry(geo)
            self.raise_()
            self.activateWindow()
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
            self.createWinId()
            handle = self.windowHandle()
            if handle is not None:
                handle.setScreen(screen)
            self.setGeometry(geo)
            self.showFullScreen()
            handle = self.windowHandle()
            if handle is not None and handle.screen() is not screen:
                handle.setScreen(screen)
                self.showFullScreen()
            self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(80, self._grab)
        print(
            f"do-something  covering {screen.name()} "
            f"{geo.x()},{geo.y()} {geo.width()}x{geo.height()}  "
            f"seed={self.world.phrase!r} hex={self.world.hex[:12]}",
            flush=True,
        )

    def _win32_topmost(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            user32.SetWindowPos(hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0040)
        except Exception:
            pass

    def _grab(self) -> None:
        try:
            self.grabKeyboard()
        except Exception:
            pass
        self.setFocus(Qt.FocusReason.OtherFocusReason)


class Windowed(QMainWindow):
    def __init__(self, world: SeedWorld, width: int, height: int):
        super().__init__()
        self.setWindowTitle(f"Do Something — {world.phrase}")
        self.resize(width, height)
        view = BusyView(world, "windowed", height > width, salt=0)
        self.setCentralWidget(view)
        for seq in ("Esc", "Q", "F11"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(QApplication.quit)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Q, Qt.Key.Key_F11):
            QApplication.quit()
            return
        super().keyPressEvent(event)


def iter_screens(app: QApplication):
    seen: set[tuple[int, int, int, int]] = set()
    screens = list(QGuiApplication.screens())
    if not screens and app.primaryScreen() is not None:
        screens = [app.primaryScreen()]
    out = []
    for screen in screens:
        if screen is None:
            continue
        geo = screen.geometry()
        key = (int(geo.x()), int(geo.y()), int(geo.width()), int(geo.height()))
        if key[2] < 1 or key[3] < 1 or key in seen:
            continue
        seen.add(key)
        out.append(screen)
    return out


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        d = base / "DoSomething"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        d = base / "do-something"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_saved_seed() -> str | None:
    path = config_dir() / "seed.txt"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def save_seed(phrase: str) -> None:
    (config_dir() / "seed.txt").write_text(phrase.strip() + "\n", encoding="utf-8")


def peel_windows_scr(argv: list[str]) -> tuple[str | None, list[str]]:
    """Windows screensaver host passes /s, /c, /p <HWND>."""
    mode = None
    rest: list[str] = []
    skip = False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        al = a.lower()
        if al in ("/s", "-s"):
            mode = "fullscreen"
        elif al.startswith("/c") or al.startswith("-c"):
            mode = "config"
        elif al in ("/p", "-p"):
            mode = "preview"
            skip = True
        elif al.startswith("/p") or al.startswith("-p"):
            mode = "preview"
        else:
            rest.append(a)
    return mode, rest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Look extremely busy on every screen.")
    p.add_argument("--windowed", "--window", action="store_true", help="Run in a window")
    p.add_argument("--dump-screens", action="store_true", help="Print screens and exit")
    p.add_argument("--smoke", metavar="PATH", help="Windowed screenshot then quit")
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--seed", default=None, help="Seed phrase (skips the prompt)")
    p.add_argument("--version", action="store_true", help="Print version and exit")
    return p.parse_args(argv)


def prompt_seed(preset: str | None) -> SeedWorld | None:
    if preset is not None:
        world = SeedWorld(preset)
        print(f"do-something  seed {world.phrase!r}  hex {world.hex[:16]}  shape {world.shape}", flush=True)
        return world
    dlg = SeedDialog()
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    world = SeedWorld(dlg.phrase())
    print(f"do-something  seed {world.phrase!r}  hex {world.hex[:16]}  shape {world.shape}", flush=True)
    return world


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    scr_mode, rest = peel_windows_scr(raw)
    args = parse_args(rest)
    if args.version:
        print(f"do-something {APP_VERSION}")
        return 0
    if scr_mode == "preview":
        return 0

    app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon = ROOT / "share" / "icon.svg"
    if not icon.exists():
        icon = ROOT / "share" / "icon.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    screens = iter_screens(app)
    if args.dump_screens:
        if not screens:
            print("do-something  no screens")
            return 1
        print(f"do-something  {len(screens)} screen(s):")
        for i, s in enumerate(screens, 1):
            g = s.geometry()
            orient = "portrait" if g.height() > g.width() else "landscape"
            print(
                f"  {i}. {s.name()}  {g.x()},{g.y()}  "
                f"{g.width()}x{g.height()}  {orient}"
            )
        return 0

    if scr_mode == "config":
        world = prompt_seed(None)
        if world is not None:
            save_seed(world.phrase)
        return 0

    preset = args.seed
    if preset is None and args.smoke:
        preset = "System Check"
    if preset is None and scr_mode == "fullscreen":
        preset = load_saved_seed()
    world = prompt_seed(preset)
    if world is None:
        return 0
    save_seed(world.phrase)

    if args.smoke or args.windowed:
        win = Windowed(world, args.width, args.height)
        win.show()
        win.raise_()
        win.activateWindow()
        if args.smoke:
            def snap():
                pix = win.grab()
                pix.save(args.smoke)
                print(f"do-something  smoke saved {args.smoke}", flush=True)
                QApplication.quit()

            QTimer.singleShot(3600, snap)
        return app.exec()

    if not screens:
        print("do-something  no screens", file=sys.stderr)
        return 1

    app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
    guard = ScreensaverGuard(grace_s=0.9, parent=app)
    app.installEventFilter(guard)
    covers: list[CoverWindow] = []

    def add_screen(screen) -> None:
        if any(c.screen_ref is screen for c in covers):
            return
        cover = CoverWindow(screen, world, salt=len(covers))
        cover.installEventFilter(guard)
        covers.append(cover)
        cover.place()

    def remove_screen(screen) -> None:
        kept = []
        for cover in covers:
            if cover.screen_ref is screen:
                cover.hide()
                cover.close()
            else:
                kept.append(cover)
        covers[:] = kept

    for screen in screens:
        add_screen(screen)
    if covers:
        QTimer.singleShot(100, lambda: covers[0].grabKeyboard())
    app.screenAdded.connect(add_screen)
    app.screenRemoved.connect(remove_screen)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
