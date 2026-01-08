""" Main script. """
"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Modules

import sys
import datetime
import globals as g
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,  QWidget, QGroupBox, QTextEdit, QSplashScreen, QMenuBar, QMenu, QAction, QSizePolicy, QLabel, QScrollArea
from PyQt5.QtGui import QTextCursor, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QThread,  QObject, pyqtSignal
from machine import *
from camera import capture_frame, CameraWidget, CameraThread, CameraControls

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Hardware profile

device_profile = {
    "servo": [
        c_char_p(b"27256526"),
        c_char_p(b"27256127"),
        c_char_p(b"27256510"),
        c_char_p(b"55152924"),
    ],
    "inertial": [
        c_char_p(b"97100512"),
    ],
    "widget": [
        None,
    ]
}

joystick_state = {"Microscope": [False] * 13,
                  "Sample Stage X-Axis": [False] * 13,
                  "Sample Stage Y-Axis": [False] * 13,
                  "Sample Stage Rotator": [False] * 13,
                  "Stamp Stage X-Axis": [False] * 13,
                  "Stamp Stage Y-Axis": [False] * 13,
                  "Stamp Stage Z-Axis": [False] * 13,
                  "Last Moved Device": [False] * 13,
                  "Last Disconnected Device": [False] * 13}

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# GUI loading page

# Stream redirect for print() → GUI logs
class EmittingStream(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        if text.strip():
            self.text_written.emit(str(text))
            sys.__stdout__.write(text)  # ✅ Also print to original terminal

    def flush(self): 
        pass

class StartupScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Autotransfer Initializing")
        self.setFixedSize(2000, 1000)

        # =============================
        # 1. Background image
        # =============================
        self.bg_label = QLabel(self)
        pixmap = QPixmap(r"C:\Users\cromm\OneDrive\Desktop\Jiahui\joystick-transfer\ctypes\2.1.7\pics\bg.jpg")

        # Fill the entire screen and crop proportionally
        scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Center the pixmap inside the window
        pixmap_x = (self.width() - scaled_pixmap.width()) // 2
        pixmap_y = (self.height() - scaled_pixmap.height()) // 2

        self.bg_label.setPixmap(scaled_pixmap)
        self.bg_label.setGeometry(pixmap_x, pixmap_y, scaled_pixmap.width(), scaled_pixmap.height())

        # =============================
        # 2. "Initializing..." text (top)
        # =============================
        self.subtitle = QLabel("Initializing...", self)
        self.subtitle.setFont(QFont("Arial", 15))
        self.subtitle.setStyleSheet("color: white;")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setFixedSize(600, 40)
        self.subtitle.move((self.width() - self.subtitle.width()) // 2, self.height() - 450)

        # =============================
        # 3. "AUTOTRANSFER" title
        # =============================
        self.title = QLabel("AUTOTRANSFER", self)
        self.title.setFont(QFont("Gill Sans Bold", 40, QFont.Bold))
        self.title.setStyleSheet("color: white;")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFixedSize(800, 60)
        self.title.move((self.width() - self.title.width()) // 2, self.height() - 250)

        # =============================
        # 4. Version info (bottom right)
        # =============================
        self.version = QLabel("v2.1.7 Designed by JN", self)
        self.version.setFont(QFont("Arial", 10))
        self.version.setStyleSheet("color: white;")
        self.version.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.version.setFixedSize(300, 20)
        self.version.move(self.width() - self.version.width() - 40, self.height() - 100)

        # =============================
        # 5. New log view container (scroll-free, auto-trim)
        self.log_container = QWidget(self)
        self.log_container.setGeometry((self.width()) // 2 - 180, self.height() - 380, 500, 100)

        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_layout.setSpacing(2)

        self.log_lines = []  # Keep track of labels
        self.max_log_lines = 6  # Limit based on height and font size

        # =============================
        # 6. Redirect print() to log area
        # =============================
        sys.stdout = EmittingStream(text_written=self.append_log)
        sys.stderr = EmittingStream(text_written=self.append_log)

    def append_log(self, message):
        label = QLabel(message)
        label.setStyleSheet("color: white; font-size: 16px; background: transparent;")
        self.log_layout.addWidget(label)
        self.log_lines.append(label)

        # Trim if over limit
        if len(self.log_lines) > self.max_log_lines:
            old_label = self.log_lines.pop(0)
            self.log_layout.removeWidget(old_label)
            time.sleep(0.1)
            old_label.deleteLater()

        QApplication.processEvents()  # Force update
# Initialize app and show splash
app = QApplication(sys.argv)
splash_screen = StartupScreen()
splash_screen.show()
app.processEvents()

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# GUI interface

window = QMainWindow()
window.setWindowTitle("Autotransfer")
window.setGeometry(100, 100, 2500, 1500)  # Specify the window size

# A. Menu bar
class MenuBar:
    def __init__(self, window):
        self.window = window
        self.menu_bar = QMenuBar(self.window)
        self.window.setMenuBar(self.menu_bar)
        self.mode_groups = {
            "wafer": [],
            "camera": [],
            # ... add other groups as needed
        }
    
        self.setup_file_menu() 
        self.setup_mode_menu()
    
    def setup_file_menu(self):
        file_menu = QMenu("File", self.menu_bar)
        self.menu_bar.addMenu(file_menu)
        self.add_action_to_menu(file_menu, "Refresh", self.refresh)
        self.add_action_to_menu(file_menu, "Save Image", self.save)
        self.add_action_to_menu(file_menu, "Exist", self.exit)
        
    def setup_mode_menu(self):
        mode_menu = QMenu("Mode", self.menu_bar)
        self.menu_bar.addMenu(mode_menu)
        self.setup_wafer_submenu(mode_menu)
        self.setup_camera_submenu(mode_menu)
    
    def setup_wafer_submenu(self, mode_menu):
        wafer_submenu = QMenu("Wafer", mode_menu)

        self.wafer_actions = {
        "Search": self.add_action_to_menu(wafer_submenu, "Search", self.search_mode, group = "wafer", checkable=True),
        "Adjust": self.add_action_to_menu(wafer_submenu, "Adjust", self.adjust_mode, group = "wafer", checkable=True)
        }
        
        mode_menu.addMenu(wafer_submenu)

    def setup_camera_submenu(self, mode_menu):
        camera_submenu = QMenu("Camera", mode_menu)

        self.camera_actions = {
            "Default": self.add_action_to_menu(camera_submenu, "Default", self.default_mode, group = "camera",checkable=True),
            "Track": self.add_action_to_menu(camera_submenu, "Tracking", self.track_mode, group = "camera",checkable=True),
            "Draw": self.add_action_to_menu(camera_submenu, "Drawing", self.draw_mode, group = "camera", checkable=True),
            "Measure": self.add_action_to_menu(camera_submenu, "Measuring", self.measure_mode, group = "camera", checkable=True)
        }

        mode_menu.addMenu(camera_submenu)


    def add_action_to_menu(self, menu, action_name, function, group=None, checkable=False):
        action = QAction(action_name, self.window)
        action.setCheckable(checkable)
        action.triggered.connect(function)
        menu.addAction(action)
        
        if group and group in self.mode_groups:
            self.mode_groups[group].append(action)

        return action
    
    def refresh(self):
        self.window.repaint()

    def save(self):
        if g.frame is not None and g.frame.size > 0:
            capture_frame(g.frame.copy(), self)
        else:
            print("Cannot capture: frame is empty or not ready.")

    def exit(self):
        self.window.close()
    
    def uncheck_group_modes(self, group_name):
        if group_name in self.mode_groups:
            for action in self.mode_groups[group_name]:
                action.setChecked(False)
    
    def search_mode(self):
        self.uncheck_group_modes('wafer')
        self.wafer_actions["Search"].setChecked(True)
        g.parameters["Sample Stage X-Axis"]["CCstep"] = 5000
        g.parameters["Sample Stage Y-Axis"]["CCstep"] = 5000
        g.parameters["Sample Stage Rotator"]["CCstep"] = 10000

    def adjust_mode(self):
        self.uncheck_group_modes('wafer')
        self.wafer_actions["Adjust"].setChecked(True)
        g.parameters["Sample Stage X-Axis"]["CCstep"] = 500
        g.parameters["Sample Stage Y-Axis"]["CCstep"] = 500
        g.parameters["Sample Stage Rotator"]["CCstep"] = 1000
    
    def default_mode(self):
        self.uncheck_group_modes('camera')
        self.camera_actions["Default"].setChecked(True)
        g.mode = "default"

    def track_mode(self):
        self.uncheck_group_modes('camera')
        self.camera_actions["Track"].setChecked(True)
        g.mode = "tracking"

    def draw_mode(self):
        self.uncheck_group_modes('camera')
        self.camera_actions["Draw"].setChecked(True)
        g.mode = "drawing"

    def measure_mode(self):
        self.uncheck_group_modes('camera')
        self.camera_actions["Measure"].setChecked(True)
        g.mode = "measuring"


# Using the class to set up the menu bar for a window
menu_setup = MenuBar(window)

"""------------------------------------------------------------------------------------"""
# B. Main layout

central_widget = QWidget()
window.setCentralWidget(central_widget)
# layout = QGridLayout()
# central_widget.setLayout(layout)  # set layout to central_widget

main_layout = QHBoxLayout()
central_widget.setLayout(main_layout)

left_column = QVBoxLayout()
center_column = QVBoxLayout()
right_column = QVBoxLayout()

main_layout.addLayout(left_column, stretch=1)  # Left GUIs
main_layout.addLayout(center_column, stretch=3)  # Camera big center
main_layout.addLayout(right_column, stretch=1)  # Right GUIs


# Create a QTextEdit for console output and add them to the layout
# console = QTextEdit()
# console.setReadOnly(True)
# layout.addWidget(console, 4, 0, 1, 2)  # Add it to the bottom row, first column

# sys.stdout = OutputRedirector(console)
# sys.stderr = OutputRedirector(console)

group_box_stylesheet = """
QGroupBox {
    font: 30px Cooper Black;/* Set the font size and style of the title */
    border: 2px solid gray; /* Set the width and color of the border */
    border-radius: 9px; /* Set the roundness of the corners */
    margin-top: 0.5em; /* Set the top margin */
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px; /* Set the left margin of the title */
    padding: 0 3px 0 3px; /* Set the padding around the title */
}
"""

camera_widget = CameraWidget()
camera_widget.setMinimumSize(1200, 300)
camera_widget.label.setScaledContents(False)
camera_widget.label.setAlignment(Qt.AlignCenter)
camera_widget.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

controls_widget = CameraControls()  # <--- This is the slider controller

# Optional: group it nicely
controls_group = QGroupBox("Image Processing")
controls_group.setStyleSheet(group_box_stylesheet)
controls_layout = QVBoxLayout()
controls_layout.addWidget(controls_widget)
controls_group.setLayout(controls_layout)

# Add widgets to the center column
center_column.addWidget(camera_widget)
center_column.addWidget(controls_group)

# Create horizontal layout to hold both "Image Processing" and "Image Analysis"
processing_and_analysis_layout = QHBoxLayout()

# Shrink Image Processing block
controls_group.setMaximumHeight(500)  # or use sizePolicy if needed
controls_group.setMaximumWidth(300)  # or use sizePolicy if needed

# Add Image Processing block
processing_and_analysis_layout.addWidget(controls_group)

# Create Image Analysis block
image_analysis_group = QGroupBox("Transfer Analysis")
image_analysis_group.setStyleSheet(group_box_stylesheet)
image_analysis_layout = QVBoxLayout()
image_analysis_group.setMaximumHeight(500)  # or use sizePolicy if needed

g.image_analysis_log = QTextEdit()
g.image_analysis_log.setReadOnly(True)
g.image_analysis_log.setStyleSheet("background-color: white; font-family: Consolas;")
# g.image_analysis_log.setMaximumHeight(150)  # ← You can adjust this value

image_analysis_layout.addWidget(g.image_analysis_log)

image_analysis_group.setLayout(image_analysis_layout)
# image_analysis_group.setVisible(False) # Analysis thread starts

# Add Image Analysis block
processing_and_analysis_layout.addWidget(image_analysis_group)

# Add the entire row to the center column
center_column.addLayout(processing_and_analysis_layout)

# Expose to other modules
    #g.image_analysis_group = image_analysis_group



camera_thread = CameraThread()
camera_thread.frame_ready.connect(camera_widget.update_image)
camera_thread.start()


# Create DeviceGUI instances and add them to the layout
microscope_gui = GUI("Microscope", device_profile["servo"][0], "servo", None, device_profile)
microscope_group = QGroupBox("Microscope")
microscope_group.setStyleSheet(group_box_stylesheet)
microscope_layout = QVBoxLayout()
microscope_layout.addWidget(microscope_gui)
microscope_group.setLayout(microscope_layout)
left_column.addWidget(microscope_group)

sample_stage_x_gui = GUI("Sample Stage X-Axis", device_profile["servo"][1], "servo", None, device_profile)
sample_stage_x_group = QGroupBox("Sample X-Axis")
sample_stage_x_group.setStyleSheet(group_box_stylesheet)
sample_stage_x_layout = QVBoxLayout()
sample_stage_x_layout.addWidget(sample_stage_x_gui)
sample_stage_x_group.setLayout(sample_stage_x_layout)
left_column.addWidget(sample_stage_x_group)

sample_stage_y_gui = GUI("Sample Stage Y-Axis", device_profile["servo"][2], "servo", None, device_profile)
sample_stage_y_group = QGroupBox("Sample Y-Axis")
sample_stage_y_group.setStyleSheet(group_box_stylesheet)
sample_stage_y_layout = QVBoxLayout()
sample_stage_y_layout.addWidget(sample_stage_y_gui)
sample_stage_y_group.setLayout(sample_stage_y_layout)
left_column.addWidget(sample_stage_y_group)

sample_stage_rotator_gui = GUI("Sample Stage Rotator", device_profile["servo"][3], "servo", None, device_profile)
sample_stage_rotator_group = QGroupBox("Sample Rotator")
sample_stage_rotator_group.setStyleSheet(group_box_stylesheet)
sample_stage_rotator_layout = QVBoxLayout()
sample_stage_rotator_layout.addWidget(sample_stage_rotator_gui)
sample_stage_rotator_group.setLayout(sample_stage_rotator_layout)
left_column.addWidget(sample_stage_rotator_group)

stamp_stage_x_gui = GUI("Stamp Stage X-Axis", device_profile["inertial"][0], "inertial", 3, device_profile)
stamp_stage_x_group = QGroupBox("Stamp X-Axis")
stamp_stage_x_group.setStyleSheet(group_box_stylesheet)
stamp_stage_x_layout = QVBoxLayout()
stamp_stage_x_layout.addWidget(stamp_stage_x_gui)
stamp_stage_x_group.setLayout(stamp_stage_x_layout)
right_column.addWidget(stamp_stage_x_group)

stamp_stage_y_gui = GUI("Stamp Stage Y-Axis", device_profile["inertial"][0], "inertial", 2, device_profile)
stamp_stage_y_group = QGroupBox("Stamp Y-Axis")
stamp_stage_y_group.setStyleSheet(group_box_stylesheet)
stamp_stage_y_layout = QVBoxLayout()
stamp_stage_y_layout.addWidget(stamp_stage_y_gui)
stamp_stage_y_group.setLayout(stamp_stage_y_layout)
right_column.addWidget(stamp_stage_y_group)

stamp_stage_z_gui = GUI("Stamp Stage Z-Axis", device_profile["inertial"][0], "inertial", 1, device_profile)
stamp_stage_z_group = QGroupBox("Stamp Z-Axis")
stamp_stage_z_group.setStyleSheet(group_box_stylesheet)
stamp_stage_z_layout = QVBoxLayout()
stamp_stage_z_layout.addWidget(stamp_stage_z_gui)
stamp_stage_z_group.setLayout(stamp_stage_z_layout)
right_column.addWidget(stamp_stage_z_group)

widget_gui = GUI("Camera", device_profile["widget"][0], "widget", None, device_profile)
g.gui_instance = widget_gui
widget_group = QGroupBox("Camera")
widget_group.setStyleSheet(group_box_stylesheet)
widget_layout = QVBoxLayout()
widget_layout.addWidget(widget_gui)
widget_group.setLayout(widget_layout)
right_column.addWidget(widget_group)

# main_layout.addLayout(devices_layout, stretch=1)

"""------------------------------------------------------------------------------------"""
# C. Device GUI list

devices_gui = [microscope_gui,
           sample_stage_x_gui,
           sample_stage_y_gui,
           sample_stage_rotator_gui,
           stamp_stage_x_gui,
           stamp_stage_y_gui,
           stamp_stage_z_gui]

device_gui_name = ["Microscope",
               "Sample Stage X-Axis",
               "Sample Stage Y-Axis",
               "Sample Stage Rotator",
               "Stamp Stage X-Axis",
               "Stamp Stage Y-Axis",
               "Stamp Stage Z-Axis",
               "Last Moved Device",
               "Last Disconnected Device"]

# QThread.sleep(10)

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""

# Real-time director
class OutputRedirector:
    def __init__(self, console):
        self.console = console
        self.buffer = []
        self.last_update_time = datetime.datetime.now()


    def write(self, text):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.buffer.append(f"[{timestamp}] {text.rstrip()}")


        # Check if enough time has passed since the last update
        if (datetime.datetime.now() - self.last_update_time).seconds >= 0.01:
            self.flush()

    def flush(self):
        # Write all buffered lines to the console
        for line in self.buffer:
            self.console.append(line)
        self.console.moveCursor(QTextCursor.End)
        self.console.ensureCursorVisible()
        self.buffer = []
        self.last_update_time = datetime.datetime.now()

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Camera

# camera_thread = threading.Thread(target=camera_main)
# camera_thread.start()

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Joystick

# Initialize Joystick instance
joystick = Joystick(devices_gui, device_gui_name)

# Start the GUI event loop
controller = Controller(devices_gui, joystick)
controller.start()

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Esc setting
# Close the splash screen and show the main window
splash_screen.close()
window.show()

def on_closing():
    camera_thread.stop()  # Add this if you created a stop() method
    for device in devices_gui:
        device.stop_device()
        device.disconnect_device()

    joystick.stop()

app.aboutToQuit.connect(on_closing)

app.exec_()