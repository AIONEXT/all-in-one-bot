"""
System Monitor Widget for AIO Bot GUI.
"""

import logging

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from aio_bot.core.bot import AIOBot
from aio_bot.monitoring.system_monitor import SystemMetrics


class SystemMonitorWidget(QWidget):
    """System monitoring widget with detailed metrics."""

    def __init__(self, bot: AIOBot):
        super().__init__()
        self.bot = bot
        self.logger = logging.getLogger("AIOBot.GUI.SystemMonitorWidget")
        self._history_points = 60
        self._cpu_history = []
        self._mem_history = []
        self._disk_history = []
        self._net_history = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup the system monitor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tabs for different views
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Overview tab
        self.overview_tab = QWidget()
        self._setup_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")

        # CPU tab
        self.cpu_tab = QWidget()
        self._setup_cpu_tab()
        self.tabs.addTab(self.cpu_tab, "CPU")

        # Memory tab
        self.memory_tab = QWidget()
        self._setup_memory_tab()
        self.tabs.addTab(self.memory_tab, "Memory")

        # Disk tab
        self.disk_tab = QWidget()
        self._setup_disk_tab()
        self.tabs.addTab(self.disk_tab, "Disk")

        # Network tab
        self.network_tab = QWidget()
        self._setup_network_tab()
        self.tabs.addTab(self.network_tab, "Network")

        # GPU tab
        self.gpu_tab = QWidget()
        self._setup_gpu_tab()
        self.tabs.addTab(self.gpu_tab, "GPU")

        # Processes tab
        self.processes_tab = QWidget()
        self._setup_processes_tab()
        self.tabs.addTab(self.processes_tab, "Processes")

    def _setup_overview_tab(self):
        """Setup overview tab with key metrics."""
        layout = QVBoxLayout(self.overview_tab)
        layout.setSpacing(16)

        # System info group
        info_group = QGroupBox("System Information")
        info_layout = QGridLayout(info_group)

        self.sys_info_labels = {}
        info_fields = [
            ("Platform", "platform"),
            ("Architecture", "architecture"),
            ("Processor", "processor"),
            ("CPU Cores", "cpu_count"),
            ("Total Memory", "memory_total_gb"),
            ("Boot Time", "boot_time"),
        ]

        for i, (label, key) in enumerate(info_fields):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel("--")
            val.setFont(QFont("Segoe UI", 9))
            info_layout.addWidget(lbl, i, 0)
            info_layout.addWidget(val, i, 1)
            self.sys_info_labels[key] = val

        layout.addWidget(info_group)

        # Real-time metrics
        metrics_group = QGroupBox("Real-time Metrics")
        metrics_layout = QGridLayout(metrics_group)

        self.overview_cards = {}
        metrics = [
            ("CPU", "cpu_percent", "%", "#0078d4", 80, 95),
            ("Memory", "memory_percent", "%", "#107c10", 85, 95),
            ("Swap", "swap_percent", "%", "#ff8c00", 50, 80),
        ]

        for i, (title, key, unit, color, warn, crit) in enumerate(metrics):
            card = self._create_metric_card(title, key, unit, color, warn, crit)
            self.overview_cards[key] = card
            metrics_layout.addWidget(card, 0, i)

        layout.addWidget(metrics_group)

        # Disk usage summary
        disk_group = QGroupBox("Disk Usage")
        disk_layout = QVBoxLayout(disk_group)

        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(5)
        self.disk_table.setHorizontalHeaderLabels(["Mount Point", "Total", "Used", "Free", "Usage"])
        self.disk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disk_table.setAlternatingRowColors(True)
        self.disk_table.setMaximumHeight(200)
        disk_layout.addWidget(self.disk_table)

        layout.addWidget(disk_group)

        layout.addStretch()

    def _setup_cpu_tab(self):
        """Setup CPU details tab."""
        layout = QVBoxLayout(self.cpu_tab)

        # Per-core usage
        cores_group = QGroupBox("Per-Core Usage")
        cores_layout = QGridLayout(cores_group)

        self.core_bars = []
        layout.addWidget(cores_group)

        # CPU frequency
        freq_group = QGroupBox("CPU Frequency")
        freq_layout = QHBoxLayout(freq_group)

        self.freq_labels = {}
        for name in ["Current", "Min", "Max"]:
            lbl = QLabel(f"{name}: -- MHz")
            freq_layout.addWidget(lbl)
            self.freq_labels[name.lower()] = lbl

        layout.addWidget(freq_group)

        # Load average
        load_group = QGroupBox("Load Average")
        load_layout = QHBoxLayout(load_group)

        self.load_labels = {}
        for name in ["1 min", "5 min", "15 min"]:
            lbl = QLabel(f"{name}: --")
            load_layout.addWidget(lbl)
            self.load_labels[name] = lbl

        layout.addWidget(load_group)

        layout.addStretch()

    def _setup_memory_tab(self):
        """Setup memory details tab."""
        layout = QVBoxLayout(self.memory_tab)

        # Virtual memory
        vm_group = QGroupBox("Virtual Memory")
        vm_layout = QGridLayout(vm_group)

        self.vm_labels = {}
        vm_fields = [
            ("Total", "total"),
            ("Available", "available"),
            ("Used", "used"),
            ("Free", "free"),
            ("Percent Used", "percent"),
            ("Buffers", "buffers"),
            ("Cached", "cached"),
        ]

        for i, (label, key) in enumerate(vm_fields):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel("--")
            vm_layout.addWidget(lbl, i // 2, (i % 2) * 2)
            vm_layout.addWidget(val, i // 2, (i % 2) * 2 + 1)
            self.vm_labels[key] = val

        layout.addWidget(vm_group)

        # Swap memory
        swap_group = QGroupBox("Swap Memory")
        swap_layout = QGridLayout(swap_group)

        self.swap_labels = {}
        swap_fields = [
            ("Total", "total"),
            ("Used", "used"),
            ("Free", "free"),
            ("Percent", "percent"),
        ]

        for i, (label, key) in enumerate(swap_fields):
            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel("--")
            swap_layout.addWidget(lbl, i // 2, (i % 2) * 2)
            swap_layout.addWidget(val, i // 2, (i % 2) * 2 + 1)
            self.swap_labels[key] = val

        layout.addWidget(swap_group)

        layout.addStretch()

    def _setup_disk_tab(self):
        """Setup disk details tab."""
        layout = QVBoxLayout(self.disk_tab)

        # Disk partitions
        parts_group = QGroupBox("Disk Partitions")
        parts_layout = QVBoxLayout(parts_group)

        self.disk_detail_table = QTableWidget()
        self.disk_detail_table.setColumnCount(7)
        self.disk_detail_table.setHorizontalHeaderLabels([
            "Device", "Mount Point", "FS Type", "Total", "Used", "Free", "Usage"
        ])
        self.disk_detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disk_detail_table.setAlternatingRowColors(True)
        parts_layout.addWidget(self.disk_detail_table)

        layout.addWidget(parts_group)

        # Disk I/O
        io_group = QGroupBox("Disk I/O")
        io_layout = QVBoxLayout(io_group)

        self.disk_io_table = QTableWidget()
        self.disk_io_table.setColumnCount(7)
        self.disk_io_table.setHorizontalHeaderLabels([
            "Device", "Read Count", "Write Count", "Read (MB)", "Write (MB)", "Read Time (ms)", "Write Time (ms)"
        ])
        self.disk_io_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disk_io_table.setAlternatingRowColors(True)
        self.disk_io_table.setMaximumHeight(200)
        io_layout.addWidget(self.disk_io_table)

        layout.addWidget(io_group)

    def _setup_network_tab(self):
        """Setup network details tab."""
        layout = QVBoxLayout(self.network_tab)

        # Network interfaces
        net_group = QGroupBox("Network Interfaces")
        net_layout = QVBoxLayout(net_group)

        self.net_table = QTableWidget()
        self.net_table.setColumnCount(9)
        self.net_table.setHorizontalHeaderLabels([
            "Interface", "Bytes Sent", "Bytes Recv", "Packets Sent", "Packets Recv",
            "Errors In", "Errors Out", "Drops In", "Drops Out"
        ])
        self.net_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.net_table.setAlternatingRowColors(True)
        net_layout.addWidget(self.net_table)

        layout.addWidget(net_group)

        # Connections
        conn_group = QGroupBox("Active Connections")
        conn_layout = QVBoxLayout(conn_group)

        self.conn_label = QLabel("Total connections: --")
        conn_layout.addWidget(self.conn_label)

        layout.addWidget(conn_group)

        layout.addStretch()

    def _setup_gpu_tab(self):
        """Setup GPU details tab."""
        layout = QVBoxLayout(self.gpu_tab)

        gpu_group = QGroupBox("GPU Devices")
        gpu_layout = QVBoxLayout(gpu_group)

        self.gpu_table = QTableWidget()
        self.gpu_table.setColumnCount(8)
        self.gpu_table.setHorizontalHeaderLabels([
            "ID", "Name", "Load %", "Memory Total", "Memory Used", "Memory Free", "Memory %", "Temp (°C)"
        ])
        self.gpu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.gpu_table.setAlternatingRowColors(True)
        gpu_layout.addWidget(self.gpu_table)

        layout.addWidget(gpu_group)

        layout.addStretch()

    def _setup_processes_tab(self):
        """Setup processes tab."""
        layout = QVBoxLayout(self.processes_tab)

        proc_group = QGroupBox("Top Processes")
        proc_layout = QVBoxLayout(proc_group)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(6)
        self.proc_table.setHorizontalHeaderLabels([
            "PID", "Name", "User", "CPU %", "Memory %", "Started"
        ])
        self.proc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.proc_table.setAlternatingRowColors(True)
        self.proc_table.setSortingEnabled(True)
        proc_layout.addWidget(self.proc_table)

        layout.addWidget(proc_group)

    def _create_metric_card(self, title: str, key: str, unit: str, color: str,
                           warn: float, crit: float) -> QFrame:
        """Create a metric card."""
        from aio_bot.gui.dashboard import MetricCard
        return MetricCard(title, "--", unit, color, warn, crit)

    def refresh(self):
        """Refresh the widget."""
        self.update_data()

    def update_data(self):
        """Update with latest metrics."""
        try:
            metrics = None
            if self.bot.system_monitor:
                metrics = self.bot.system_monitor.get_latest_metrics()

            if not metrics:
                return

            # Update system info (once)
            if not hasattr(self, '_sys_info_set'):
                summary = self.bot.system_monitor.get_system_summary()
                self.sys_info_labels["platform"].setText(f"{summary.get('platform', 'Unknown')}")
                self.sys_info_labels["architecture"].setText(summary.get('architecture', 'Unknown'))
                self.sys_info_labels["processor"].setText(summary.get('processor', 'Unknown'))
                self.sys_info_labels["cpu_count"].setText(str(summary.get('cpu', {}).get('cores', 'Unknown')))
                self.sys_info_labels["memory_total_gb"].setText(f"{summary.get('memory', {}).get('total_gb', 0):.1f} GB")
                self._sys_info_set = True

            # Update overview cards
            self.overview_cards["cpu_percent"].update_value(f"{metrics.cpu_percent:.1f}", metrics.cpu_percent)
            self.overview_cards["memory_percent"].update_value(f"{metrics.memory_percent:.1f}", metrics.memory_percent)
            self.overview_cards["swap_percent"].update_value(f"{metrics.swap_percent:.1f}", metrics.swap_percent)

            # Update CPU tab
            self._update_cpu_tab(metrics)

            # Update Memory tab
            self._update_memory_tab(metrics)

            # Update Disk tab
            self._update_disk_tab(metrics)

            # Update Network tab
            self._update_network_tab(metrics)

            # Update GPU tab
            self._update_gpu_tab(metrics)

            # Update Processes tab
            self._update_processes_tab(metrics)

        except Exception as e:
            self.logger.error("System monitor update error: %s", e)

    def _update_cpu_tab(self, metrics: SystemMetrics):
        """Update CPU tab."""
        # Per-core
        if not self.core_bars:
            # Create bars for each core
            from PySide6.QtWidgets import QLabel, QProgressBar
            cores_layout = self.cpu_tab.findChild(QGroupBox, "Per-Core Usage").layout()

            for i, core_pct in enumerate(metrics.cpu_per_core):
                row = i // 4
                col = (i % 4) * 2

                lbl = QLabel(f"Core {i}:")
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(int(core_pct))
                bar.setFormat(f"{core_pct:.1f}%")

                cores_layout.addWidget(lbl, row, col)
                cores_layout.addWidget(bar, row, col + 1)
                self.core_bars.append((lbl, bar))
        else:
            for i, (lbl, bar) in enumerate(self.core_bars):
                if i < len(metrics.cpu_per_core):
                    bar.setValue(int(metrics.cpu_per_core[i]))
                    bar.setFormat(f"{metrics.cpu_per_core[i]:.1f}%")

        # Frequency
        self.freq_labels["current"].setText(f"Current: {metrics.cpu_freq_mhz:.0f} MHz")

        # Load average
        if metrics.load_average:
            for i, name in enumerate(["1 min", "5 min", "15 min"]):
                if i < len(metrics.load_average):
                    self.load_labels[name].setText(f"{name}: {metrics.load_average[i]:.2f}")

    def _update_memory_tab(self, metrics: SystemMetrics):
        """Update memory tab."""
        import psutil

        mem = psutil.virtual_memory()
        self.vm_labels["total"].setText(self._format_bytes(mem.total))
        self.vm_labels["available"].setText(self._format_bytes(mem.available))
        self.vm_labels["used"].setText(self._format_bytes(mem.used))
        self.vm_labels["free"].setText(self._format_bytes(mem.free))
        self.vm_labels["percent"].setText(f"{mem.percent:.1f}%")
        self.vm_labels["buffers"].setText(self._format_bytes(getattr(mem, 'buffers', 0)))
        self.vm_labels["cached"].setText(self._format_bytes(getattr(mem, 'cached', 0)))

        swap = psutil.swap_memory()
        self.swap_labels["total"].setText(self._format_bytes(swap.total))
        self.swap_labels["used"].setText(self._format_bytes(swap.used))
        self.swap_labels["free"].setText(self._format_bytes(swap.free))
        self.swap_labels["percent"].setText(f"{swap.percent:.1f}%")

    def _update_disk_tab(self, metrics: SystemMetrics):
        """Update disk tab."""
        # Partitions
        self.disk_detail_table.setRowCount(len(metrics.disk_usage))
        for row, (mount, usage) in enumerate(metrics.disk_usage.items()):
            self.disk_detail_table.setItem(row, 0, QTableWidgetItem(usage.get("device", "Unknown")))
            self.disk_detail_table.setItem(row, 1, QTableWidgetItem(mount))
            self.disk_detail_table.setItem(row, 2, QTableWidgetItem(usage.get("fstype", "Unknown")))
            self.disk_detail_table.setItem(row, 3, QTableWidgetItem(self._format_bytes(usage["total"])))
            self.disk_detail_table.setItem(row, 4, QTableWidgetItem(self._format_bytes(usage["used"])))
            self.disk_detail_table.setItem(row, 5, QTableWidgetItem(self._format_bytes(usage["free"])))

            usage_item = QTableWidgetItem(f"{usage['percent']:.1f}%")
            if usage['percent'] >= 90:
                usage_item.setForeground(QColor("#d13438"))
            elif usage['percent'] >= 80:
                usage_item.setForeground(QColor("#ff8c00"))
            self.disk_detail_table.setItem(row, 6, usage_item)

        # Disk I/O
        self.disk_io_table.setRowCount(len(metrics.disk_io))
        for row, (disk, io) in enumerate(metrics.disk_io.items()):
            self.disk_io_table.setItem(row, 0, QTableWidgetItem(disk))
            self.disk_io_table.setItem(row, 1, QTableWidgetItem(f"{io['read_count']:,}"))
            self.disk_io_table.setItem(row, 2, QTableWidgetItem(f"{io['write_count']:,}"))
            self.disk_io_table.setItem(row, 3, QTableWidgetItem(f"{io['read_bytes'] / (1024*1024):.1f}"))
            self.disk_io_table.setItem(row, 4, QTableWidgetItem(f"{io['write_bytes'] / (1024*1024):.1f}"))
            self.disk_io_table.setItem(row, 5, QTableWidgetItem(f"{io['read_time']:.1f}"))
            self.disk_io_table.setItem(row, 6, QTableWidgetItem(f"{io['write_time']:.1f}"))

        # Overview disk table
        self.disk_table.setRowCount(len(metrics.disk_usage))
        for row, (mount, usage) in enumerate(metrics.disk_usage.items()):
            self.disk_table.setItem(row, 0, QTableWidgetItem(mount))
            self.disk_table.setItem(row, 1, QTableWidgetItem(self._format_bytes(usage["total"])))
            self.disk_table.setItem(row, 2, QTableWidgetItem(self._format_bytes(usage["used"])))
            self.disk_table.setItem(row, 3, QTableWidgetItem(self._format_bytes(usage["free"])))

            usage_item = QTableWidgetItem(f"{usage['percent']:.1f}%")
            if usage['percent'] >= 90:
                usage_item.setForeground(QColor("#d13438"))
            elif usage['percent'] >= 80:
                usage_item.setForeground(QColor("#ff8c00"))
            self.disk_table.setItem(row, 4, usage_item)

    def _update_network_tab(self, metrics: SystemMetrics):
        """Update network tab."""
        # Interfaces
        self.net_table.setRowCount(len(metrics.network_io))
        for row, (nic, io) in enumerate(metrics.network_io.items()):
            self.net_table.setItem(row, 0, QTableWidgetItem(nic))
            self.net_table.setItem(row, 1, QTableWidgetItem(self._format_bytes(io["bytes_sent"])))
            self.net_table.setItem(row, 2, QTableWidgetItem(self._format_bytes(io["bytes_recv"])))
            self.net_table.setItem(row, 3, QTableWidgetItem(f"{io['packets_sent']:,}"))
            self.net_table.setItem(row, 4, QTableWidgetItem(f"{io['packets_recv']:,}"))
            self.net_table.setItem(row, 5, QTableWidgetItem(str(io["errin"])))
            self.net_table.setItem(row, 6, QTableWidgetItem(str(io["errout"])))
            self.net_table.setItem(row, 7, QTableWidgetItem(str(io["dropin"])))
            self.net_table.setItem(row, 8, QTableWidgetItem(str(io["dropout"])))

        self.conn_label.setText(f"Total connections: {metrics.network_connections}")

    def _update_gpu_tab(self, metrics: SystemMetrics):
        """Update GPU tab."""
        self.gpu_table.setRowCount(len(metrics.gpu_metrics))
        for row, gpu in enumerate(metrics.gpu_metrics):
            self.gpu_table.setItem(row, 0, QTableWidgetItem(str(gpu["id"])))
            self.gpu_table.setItem(row, 1, QTableWidgetItem(gpu["name"]))
            self.gpu_table.setItem(row, 2, QTableWidgetItem(f"{gpu['load']:.1f}%"))
            self.gpu_table.setItem(row, 3, QTableWidgetItem(f"{gpu['memory_total']} MB"))
            self.gpu_table.setItem(row, 4, QTableWidgetItem(f"{gpu['memory_used']} MB"))
            self.gpu_table.setItem(row, 5, QTableWidgetItem(f"{gpu['memory_free']} MB"))
            self.gpu_table.setItem(row, 6, QTableWidgetItem(f"{gpu['memory_percent']:.1f}%"))
            self.gpu_table.setItem(row, 7, QTableWidgetItem(f"{gpu['temperature']}°C"))

    def _update_processes_tab(self, metrics: SystemMetrics):
        """Update processes tab."""
        self.proc_table.setRowCount(len(metrics.top_processes))
        for row, proc in enumerate(metrics.top_processes):
            self.proc_table.setItem(row, 0, QTableWidgetItem(str(proc["pid"])))
            self.proc_table.setItem(row, 1, QTableWidgetItem(proc["name"]))
            self.proc_table.setItem(row, 2, QTableWidgetItem(proc.get("username", "Unknown")))
            self.proc_table.setItem(row, 3, QTableWidgetItem(f"{proc['cpu_percent']:.1f}"))
            self.proc_table.setItem(row, 4, QTableWidgetItem(f"{proc['memory_percent']:.1f}"))
            self.proc_table.setItem(row, 5, QTableWidgetItem(proc.get("create_time", "Unknown")))

    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} PB"
