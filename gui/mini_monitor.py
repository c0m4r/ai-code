import sys
import psutil
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QGridLayout
from PyQt5.QtCore import QTimer

class Monitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Resource Monitor")
        self.layout = QVBoxLayout()
        self.grid = QGridLayout()
        self.labels = {
            "cpu": QLabel(),
            "ram": QLabel(),
            "swap": QLabel(),
            "load": QLabel(),
            "net_up": QLabel(),
            "net_down": QLabel(),
        }
        self.grid.addWidget(QLabel("CPU Usage:"), 0, 0)
        self.grid.addWidget(self.labels["cpu"], 0, 1)
        self.grid.addWidget(QLabel("RAM Usage:"), 1, 0)
        self.grid.addWidget(self.labels["ram"], 1, 1)
        self.grid.addWidget(QLabel("Swap Usage:"), 2, 0)
        self.grid.addWidget(self.labels["swap"], 2, 1)
        self.grid.addWidget(QLabel("Load Average:"), 3, 0)
        self.grid.addWidget(self.labels["load"], 3, 1)
        self.grid.addWidget(QLabel("Network Upload:"), 4, 0)
        self.grid.addWidget(self.labels["net_up"], 4, 1)
        self.grid.addWidget(QLabel("Network Download:"), 5, 0)
        self.grid.addWidget(self.labels["net_down"], 5, 1)
        self.layout.addLayout(self.grid)
        self.setLayout(self.layout)

        self.prev_net = psutil.net_io_counters()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def update_stats(self):
        self.labels["cpu"].setText(f"{psutil.cpu_percent(interval=None)} %")
        mem = psutil.virtual_memory()
        self.labels["ram"].setText(f"{mem.percent} % ({self._bytes(mem.used)}/{self._bytes(mem.total)})")
        swap = psutil.swap_memory()
        self.labels["swap"].setText(f"{swap.percent} % ({self._bytes(swap.used)}/{self._bytes(swap.total)})")
        if hasattr(psutil, "getloadavg"):
            load1, load5, load15 = psutil.getloadavg()
            self.labels["load"].setText(f"{load1:.2f}, {load5:.2f}, {load15:.2f}")
        else:
            self.labels["load"].setText("N/A")
        cur_net = psutil.net_io_counters()
        up_speed = cur_net.bytes_sent - self.prev_net.bytes_sent
        down_speed = cur_net.bytes_recv - self.prev_net.bytes_recv
        self.labels["net_up"].setText(f"{self._bytes(up_speed)}/s")
        self.labels["net_down"].setText(f"{self._bytes(down_speed)}/s")
        self.prev_net = cur_net

    def _bytes(self, num):
        for unit in ["B","KB","MB","GB","TB"]:
            if num < 1024.0:
                return f"{num:.1f}{unit}"
            num /= 1024.0
        return f"{num:.1f}PB"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Monitor()
    w.show()
    sys.exit(app.exec_())
