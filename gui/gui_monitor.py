#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import psutil
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QProgressBar,
    QFrame,
)

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def fmt_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024.0:
            return f"{num:.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"


def fmt_mbps(num_bytes: int) -> str:
    mbps = num_bytes * 8 / 1_000_000
    return f"{mbps:.2f} Mbps"


# --------------------------------------------------------------------------- #
# Main widget
# --------------------------------------------------------------------------- #
class SystemMonitor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("🖥️ System Resource Monitor")
        self.setMinimumSize(420, 300)
        self._apply_palette()
        self._build_ui()
        self._prev_net = psutil.net_io_counters()
        self._timer = QTimer(self, interval=1000, timeout=self._update)
        self._timer.start()

    # ------------------------------------------------------------------- #
    # UI construction
    # ------------------------------------------------------------------- #
    def _apply_palette(self) -> None:
        dark = QPalette()
        dark.setColor(QPalette.Window, QColor("#1e1e2f"))
        dark.setColor(QPalette.WindowText, Qt.white)
        dark.setColor(QPalette.Base, QColor("#2e2e3e"))
        dark.setColor(QPalette.AlternateBase, QColor("#3e3e4e"))
        dark.setColor(QPalette.ToolTipBase, Qt.white)
        dark.setColor(QPalette.ToolTipText, Qt.white)
        dark.setColor(QPalette.Text, Qt.white)
        dark.setColor(QPalette.Button, QColor("#2e2e3f"))
        dark.setColor(QPalette.ButtonText, Qt.white)
        dark.setColor(QPalette.Highlight, QColor("#3a7bd5"))
        dark.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ----- Title ---------------------------------------------------- #
        title = QLabel("System Resource Monitor")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #3a7bd5;")
        main_layout.addWidget(title)

        # ----- Grid ------------------------------------------------------ #
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)

        # CPU
        self.cpu_bar = self._make_bar("#ff6f61")
        self.cpu_label = QLabel()
        grid.addWidget(QLabel("CPU:"), 0, 0, alignment=Qt.AlignRight)
        grid.addWidget(self.cpu_bar, 0, 1)
        grid.addWidget(self.cpu_label, 0, 2)

        # RAM
        self.ram_bar = self._make_bar("#ffb74d")
        self.ram_label = QLabel()
        grid.addWidget(QLabel("RAM:"), 1, 0, alignment=Qt.AlignRight)
        grid.addWidget(self.ram_bar, 1, 1)
        grid.addWidget(self.ram_label, 1, 2)

        # Swap
        self.swap_bar = self._make_bar("#4db6ac")
        self.swap_label = QLabel()
        grid.addWidget(QLabel("Swap:"), 2, 0, alignment=Qt.AlignRight)
        grid.addWidget(self.swap_bar, 2, 1)
        grid.addWidget(self.swap_label, 2, 2)

        # Load average
        self.load_label = QLabel()
        grid.addWidget(QLabel("Load Avg.:"), 3, 0, alignment=Qt.AlignRight)
        grid.addWidget(self.load_label, 3, 1, 1, 2)

        # Network
        self.net_up_label = QLabel()
        self.net_down_label = QLabel()
        grid.addWidget(QLabel("Upload:"), 4, 0, alignment=Qt.AlignRight)
        grid.addWidget(self.net_up_label, 4, 1, 1, 2)
        grid.addWidget(QLabel("Download:"), 5, 0, alignment=Qt.AlignRight)
        grid.addWidget(self.net_down_label, 5, 1, 1, 2)

        # ----- Separator ------------------------------------------------ #
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("color: #555555;")
        main_layout.addLayout(grid)
        main_layout.addWidget(sep)

        # Footer
        footer = QLabel("© 2024 • Powered by psutil • PyQt5")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #777777; font-size: 9pt;")
        main_layout.addWidget(footer)

    def _make_bar(self, color: str) -> QProgressBar:
        bar = QProgressBar()
        bar.setTextVisible(False)
        bar.setMaximum(100)
        bar.setMinimum(0)
        bar.setFixedHeight(14)
        bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #444;
                border-radius: 7px;
                background-color: #2e2e3e;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 7px;
            }}
            """
        )
        return bar

    # ------------------------------------------------------------------- #
    # Update loop
    # ------------------------------------------------------------------- #
    def _update(self) -> None:
        # CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        self.cpu_bar.setValue(int(cpu_pct))
        self.cpu_label.setText(f"{cpu_pct:.1f}%")

        # RAM
        vm = psutil.virtual_memory()
        self.ram_bar.setValue(int(vm.percent))
        self.ram_label.setText(f"{vm.percent:.1f}% ({fmt_bytes(vm.used)}/{fmt_bytes(vm.total)})")

        # Swap
        sm = psutil.swap_memory()
        self.swap_bar.setValue(int(sm.percent))
        self.swap_label.setText(f"{sm.percent:.1f}% ({fmt_bytes(sm.used)}/{fmt_bytes(sm.total)})")

        # Load average
        if hasattr(psutil, "getloadavg"):
            la1, la5, la15 = psutil.getloadavg()
            self.load_label.setText(f"{la1:.2f}, {la5:.2f}, {la15:.2f}")
        else:
            self.load_label.setText("N/A")

        # Network
        cur = psutil.net_io_counters()
        up_bytes = cur.bytes_sent - self._prev_net.bytes_sent
        down_bytes = cur.bytes_recv - self._prev_net.bytes_recv
        self.net_up_label.setText(fmt_mbps(up_bytes))
        self.net_down_label.setText(fmt_mbps(down_bytes))
        self._prev_net = cur


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    monitor = SystemMonitor()
    monitor.show()
    sys.exit(app.exec_())
