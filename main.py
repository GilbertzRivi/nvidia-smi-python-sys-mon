import psutil
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QGridLayout,
)
import pyqtgraph as pg
from pynvml import *
import colorsys


def generate_color_list(num):
    color_list = []
    for i in range(num):
        hue = i / num  # Vary the hue evenly
        rgb_color = colorsys.hsv_to_rgb(hue, 0.7, 0.9)  # Adjusted saturation and value
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(rgb_color[0] * 255), int(rgb_color[1] * 255), int(rgb_color[2] * 255)
        )
        color_list.append(hex_color)
    return color_list


class SystemMonitor(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuration Data
        self.config = {
            "refresh_time": 1000,
            "num_display_items": 60,
            "y_range_cpu": [0, 100],
            "y_range_core": [0, 100],
            "y_range_memory": [0, 64],
            "y_range_gpu": [0, 100],
            "y_range_cpu_frequency": [0, 4000],
            "y_range_gpu_frequency": [0, 3000],
            "window_geometry": [0, 0, 800, 600],  # Adjusted window size
            "num_columns": 2,
            "antialiasing": True,
            "chart_background_color": "#151515",  # Default white color
        }

        self.setWindowTitle("System Monitor")
        self.setGeometry(*self.config.get("window_geometry"))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QGridLayout()
        self.central_widget.setLayout(self.layout)

        # Create Charts
        self.cpu_chart = self.create_chart(
            "CPU Info",
            "% Usage",
            self.config.get("y_range_cpu"),
        )
        self.frequency_cpu_chart = self.create_chart(
            "CPU Frequency",
            "MHz",
            self.config.get("y_range_cpu_frequency"),
        )
        self.gpu_chart = self.create_chart(
            "GPU Info",
            "% Usage",
            self.config.get("y_range_gpu"),
        )
        self.frequency_gpu_chart = self.create_chart(
            "GPU Frequency",
            "MHz",
            self.config.get("y_range_gpu_frequency"),
        )
        self.memory_chart = self.create_chart(
            "Memory Usage",
            "GB",
            self.config.get("y_range_memory"),
        )
        self.drive_chart = self.create_chart(
            "Drive Usage",
            "MB/s",
            self.config.get("y_range_drive"),
        )
        self.network_chart = self.create_chart(
            "Network Usage",
            "MB/s",
            self.config.get("y_range_network"),
        )
        self.core_chart = self.create_chart(
            "CPU Core Usage",
            "Percentage",
            self.config.get("y_range_core"),
        )

        self.charts = [
            self.cpu_chart,
            self.frequency_cpu_chart,
            self.gpu_chart,
            self.frequency_gpu_chart,
            self.memory_chart,
            self.drive_chart,
            self.network_chart,
        ]

        # Add Charts to Layout
        for i, chart in enumerate(self.charts):
            row = i // self.config["num_columns"]
            col = i % self.config["num_columns"]
            self.layout.addWidget(chart, row, col)

        # Initialize Data
        self.init_data()

        # Update Charts
        self.update_charts()

    def create_chart(self, title, y_label, y_range):
        chart = pg.PlotWidget(title=title, antialias=self.config["antialiasing"])
        chart.setLabel("left", y_label)
        if y_range:
            chart.setYRange(y_range[0], y_range[1])
        chart.setBackground(self.config["chart_background_color"])
        return chart

    def init_data(self):
        # Initialize CPU frequency data
        self.frequency_cpu_data = [0] * self.config["num_display_items"]
        self.frequency_gpu_data = [0] * self.config["num_display_items"]

        # Initialize other data
        self.cpu_data = [0] * self.config["num_display_items"]
        self.core_data = [0 for _ in range(psutil.cpu_count())]
        self.memory_data = [0] * self.config["num_display_items"]
        self.drive_data = [0] * self.config["num_display_items"]
        self.network_data = [
            [0] * self.config["num_display_items"],
            [0] * self.config["num_display_items"],
        ]  # Download, Upload
        self.gpu_data = [0] * self.config["num_display_items"]
        self.drive_read_data = [0] * self.config["num_display_items"]
        self.drive_write_data = [0] * self.config["num_display_items"]
        self.cpu_temp_data = [0] * self.config["num_display_items"]
        self.gpu_temp_data = [0] * self.config["num_display_items"]
        self.layout.addWidget(self.core_chart)

        self.core_bars = pg.BarGraphItem(
            x=list(range(psutil.cpu_count())),
            height=[0] * psutil.cpu_count(),
            width=0.5,
            brushes=generate_color_list(psutil.cpu_count()),
        )
        self.core_chart.addItem(self.core_bars)

    def update_charts(self):
        # CPU
        self.cpu_chart.clear()
        self.frequency_cpu_chart.clear()
        cpu_percent = psutil.cpu_percent()

        # Get CPU temperature if available
        cpu_temp_data = psutil.sensors_temperatures()
        cpu_temp = None
        if "k10temp" in cpu_temp_data:
            for sensor in cpu_temp_data["k10temp"]:
                if sensor.label == "Tctl":
                    cpu_temp = sensor.current
                    break

        # If CPU temperature is not available, set it to 0
        if cpu_temp is None:
            cpu_temp = 0

        # Get CPU frequency
        cpu_freq = psutil.cpu_freq().current

        # Append data to the respective lists
        self.cpu_data.append(cpu_percent)
        self.cpu_temp_data.append(cpu_temp)
        self.frequency_cpu_data.append(cpu_freq)

        # Pop old data if exceeds the display limit
        if len(self.cpu_data) > self.config["num_display_items"]:
            self.cpu_data.pop(0)
            self.cpu_temp_data.pop(0)
            self.frequency_cpu_data.pop(0)

        # Update CPU usage, frequency, and temperature lines on the CPU chart
        self.update_chart_data(self.cpu_chart, self.cpu_data, pen="b")
        self.update_chart_data(
            self.cpu_chart, self.cpu_temp_data, pen="r"
        )  # Red for temperature
        self.update_chart_data(
            self.frequency_cpu_chart, self.frequency_cpu_data, pen="g"
        )

        # CPU Cores
        core_percents = psutil.cpu_percent(percpu=True)
        self.core_bars.setOpts(
            height=core_percents
        )  # Update heights of the bars every second

        # Memory
        self.memory_chart.clear()
        memory_usage = psutil.virtual_memory().used / (1024**3)  # in GB
        self.memory_data.append(memory_usage)
        self.memory_data.pop(0)
        self.update_chart_data(self.memory_chart, self.memory_data)

        # Drive
        self.drive_chart.clear()
        disk_io = psutil.disk_io_counters()
        disk_read_mb = disk_io.read_bytes / (1024**2) / 1e6  # Convert to MB/s
        disk_write_mb = disk_io.write_bytes / (1024**2) / 1e6  # Convert to MB/s

        # Append data to separate lists for read and write speeds
        self.drive_read_data.append(disk_read_mb)
        self.drive_write_data.append(disk_write_mb)

        # Pop old data if exceeds the display limit
        if len(self.drive_read_data) > self.config["num_display_items"]:
            self.drive_read_data.pop(0)
        if len(self.drive_write_data) > self.config["num_display_items"]:
            self.drive_write_data.pop(0)

        # Update read and write lines on the drive chart
        self.update_chart_data(self.drive_chart, self.drive_read_data, pen="b")
        self.update_chart_data(self.drive_chart, self.drive_write_data, pen="r")

        # Network
        self.network_chart.clear()
        net_io = psutil.net_io_counters()
        net_download_mb = net_io.bytes_recv / (1024**2) / 1e6  # Convert to MB/s
        net_upload_mb = net_io.bytes_sent / (1024**2) / 1e6  # Convert to MB/s
        self.network_data[0].append(net_download_mb)
        self.network_data[1].append(net_upload_mb)
        self.network_data[0].pop(0)
        self.network_data[1].pop(0)
        self.update_chart_data(self.network_chart, self.network_data[0], pen="b")
        self.update_chart_data(self.network_chart, self.network_data[1], pen="r")

        # GPU
        self.gpu_chart.clear()
        handle = nvmlDeviceGetHandleByIndex(0)  # Assuming only one GPU is present
        gpu_utilization = nvmlDeviceGetUtilizationRates(handle).gpu
        self.gpu_data.append(gpu_utilization)

        # Get GPU temperature
        gpu_temp_data = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        gpu_temp = gpu_temp_data
        self.gpu_temp_data.append(gpu_temp)

        # GPU Frequency
        self.frequency_gpu_chart.clear()
        handle = nvmlDeviceGetHandleByIndex(0)  # Assuming only one GPU is present
        gpu_freq_data = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS)
        gpu_freq = gpu_freq_data
        self.frequency_gpu_data.append(gpu_freq)

        # Pop old data if exceeds the display limit
        if len(self.gpu_data) > self.config["num_display_items"]:
            self.gpu_data.pop(0)
            self.gpu_temp_data.pop(0)

        # Pop old data if exceeds the display limit
        if len(self.frequency_gpu_data) > self.config["num_display_items"]:
            self.frequency_gpu_data.pop(0)

        # Update GPU usage, temperature, and frequency lines on the GPU chart
        self.update_chart_data(self.gpu_chart, self.gpu_data, pen="b")
        self.update_chart_data(
            self.gpu_chart, self.gpu_temp_data, pen="r"
        )  # Red for temperature
        self.update_chart_data(
            self.frequency_gpu_chart, self.frequency_gpu_data, pen="g"
        )

        QTimer.singleShot(
            self.config["refresh_time"], self.update_charts
        )  # Update every second

    def update_chart_data(self, chart, data, x_range=None, pen="b"):
        chart.plot(data, pen=pen)
        if x_range is not None:
            chart.setXRange(0, len(data), padding=0)


if __name__ == "__main__":
    nvmlInit()
    app = QApplication([])
    monitor = SystemMonitor()
    monitor.show()
    sys.exit(app.exec_())
