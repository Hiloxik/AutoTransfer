""" GUI script. """
"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Modules

import json
import time
import pyvisa
from queue import Queue, Empty
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QGridLayout, QWidget, QFrame, \
    QMessageBox, QCheckBox, QVBoxLayout, QGroupBox, QFileDialog
from PyQt5.QtGui import QFont, QDoubleValidator, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5 import QtCore


import globals as g
from position import *
from connectivity import *
from movement import *
from camera import get_polygon, get_polygon_tracker, get_shift, get_angle, zoom_in_camera, \
    zoom_out_camera, \
    capture_frame, calculate_color_uniformity, CameraWidget, CameraThread
from maths import *
from pyvisa import constants

from joystick import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer
import math

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# GUI layout & functions

class GUI(QMainWindow):

    def __init__(self, device_name, device_serial_num, device_type, device_channel, device_profile):
        super().__init__()

        self.device_name = device_name
        self.device_serial_num = device_serial_num
        self.device_type = device_type
        self.device_channel = device_channel
        self.device_CCdriver = DeviceCCDriver()
        self.device_profile = device_profile
        self.camera_widget = CameraWidget()
        self.alignment_running = False  # Flag to control alignment threads

        # Create a queue for real-time position reading
        # self.stop_position_update_event = threading.Event()
        # self.stop_event = threading.Event()
        # self.position_queue = Queue()

        self.initGUI()
    
    """------------------------------------------------------------------------------------"""
    # A. Layout

    def initGUI(self):
        self.setWindowTitle('Device GUI')
        self.setGeometry(100, 100, 800, 600)

        widget = QWidget(self)
        self.setCentralWidget(widget)

        grid = QGridLayout()
        widget.setLayout(grid)

        # Buttons and labels inside choices_frame with custom colors and font
        label_font = QFont("Arial", 10)
        label_font.setBold(True)

        button_font = QFont("Arial", 10)
        button_size = 50
        big_button_font = QFont("Arial", 20)
        big_button_size = 200
        radius = button_size // 2

        # Create frames for special widgets: camera
        if self.device_type == "widget":

            # Camera label
            camera_label = QLabel(f"Basler Ace acA1920-40uc", self)
            font = QFont("Arial")
            font.setPointSize(12)  # Set the font size to 14 points
            camera_label.setFont(font)
            grid.addWidget(camera_label, 0, 0)

            # Camera status
            self.status_label = QLabel("Camera connected successfully.", self)
            font = QFont("Arial")
            font.setPointSize(12)  # Set the font size to 14 points
            self.status_label.setFont(font)
            grid.addWidget(self.status_label, 1, 0)

            # Open camera
            self.open_camera_button = QPushButton('Open Camera')
            self.open_camera_button.setFont(button_font)
            self.open_camera_button.setStyleSheet("background-color: HoneyDew;")
            self.open_camera_button.pressed.connect(self.open_camera)
            self.open_camera_button.setMinimumHeight(70)
            grid.addWidget(self.open_camera_button, 2, 0)


            # Capture screen
            self.capture_button = QPushButton('Capture')
            self.capture_button.setFont(button_font)
            self.capture_button.setStyleSheet("background-color: HoneyDew;")
            self.capture_button.pressed.connect(self.capture)
            self.capture_button.setMinimumHeight(70)
            grid.addWidget(self.capture_button, 3, 0)

            # Tracking mode
            tracker_widget = QWidget()
            tracker_layout = QVBoxLayout()
            self.tracker_image = QLabel()
            pixmap = QPixmap(r"C:\Users\cromm\OneDrive\Desktop\Jiahui\joystick-transfer\ctypes\2.1.7\pics\tracker.png")
            self.tracker_image.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            self.tracker_image.mousePressEvent = self.trigger_mode1
            tracker_layout.addWidget(self.tracker_image, alignment=Qt.AlignCenter)
            tracker_widget.setLayout(tracker_layout)
            grid.addWidget(tracker_widget, 0, 1)

            # Drawing mode
            pen_widget = QWidget()
            pen_layout = QVBoxLayout()
            self.pen_image = QLabel()
            pixmap = QPixmap(r"C:\Users\cromm\OneDrive\Desktop\Jiahui\joystick-transfer\ctypes\2.1.7\pics\pen.png")
            self.pen_image.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            self.pen_image.mousePressEvent = self.trigger_mode2
            pen_layout.addWidget(self.pen_image, alignment=Qt.AlignCenter)
            pen_widget.setLayout(pen_layout)
            grid.addWidget(pen_widget, 1, 1)

            # Measuring mode
            ruler_widget = QWidget()
            ruler_layout = QVBoxLayout()
            self.ruler_image = QLabel()
            pixmap = QPixmap(r"C:\Users\cromm\OneDrive\Desktop\Jiahui\joystick-transfer\ctypes\2.1.7\pics\ruler.png")
            self.ruler_image.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            self.ruler_image.mousePressEvent = self.trigger_mode3
            ruler_layout.addWidget(self.ruler_image, alignment=Qt.AlignCenter)
            ruler_widget.setLayout(ruler_layout)
            grid.addWidget(ruler_widget, 2, 1)

            # Zoom in
            self.zoom_in_button = QPushButton('+')
            self.zoom_in_button.setFont(button_font)
            self.zoom_in_button.setFixedSize(button_size, button_size)
            self.zoom_in_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Ivory;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: FireBrick;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.zoom_in_button.pressed.connect(self.zoom_in)
            grid.addWidget(self.zoom_in_button, 0, 4)

            # Zoom out
            self.zoom_out_button = QPushButton('-')
            self.zoom_out_button.setFont(button_font)
            self.zoom_out_button.setFixedSize(button_size, button_size)
            self.zoom_out_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Ivory;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: LightGray;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.zoom_out_button.pressed.connect(self.zoom_out)
            grid.addWidget(self.zoom_out_button, 1, 4)

            # Fivefold Mirror
            self.fivefold_button = QPushButton('5X')
            self.fivefold_button.setFont(button_font)
            self.fivefold_button.setFixedSize(button_size, button_size)
            self.fivefold_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Crimson;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: LightGray;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.fivefold_button.pressed.connect(self.fivefold)
            grid.addWidget(self.fivefold_button, 0, 2)

            # Tenfold Mirror
            self.tenfold_button = QPushButton('10X')
            self.tenfold_button.setFont(button_font)
            self.tenfold_button.setFixedSize(button_size, button_size)
            self.tenfold_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Gold;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: GoldenRod;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.tenfold_button.pressed.connect(self.tenfold)
            grid.addWidget(self.tenfold_button, 1, 2)

            # Tenfold Mirror
            self.twentyfold_button = QPushButton('20X')
            self.twentyfold_button.setFont(button_font)
            self.twentyfold_button.setFixedSize(button_size, button_size)
            self.twentyfold_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: LawnGreen;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: LimeGreen;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.twentyfold_button.pressed.connect(self.twentyfold)
            grid.addWidget(self.twentyfold_button, 2, 2)

            # Retrieve Polygon
            self.retrieve_polygon_button = QPushButton('Retrieve Flake')
            self.retrieve_polygon_button.setFont(button_font)
            self.retrieve_polygon_button.setStyleSheet("background-color: Ivory;")
            self.retrieve_polygon_button.pressed.connect(self.retrieve_polygon)
            grid.addWidget(self.retrieve_polygon_button, 0, 3)

            # Calibrate Polygon
            self.calibrate_button = QPushButton('Calibrate Flake')
            self.calibrate_button.pressed.connect(self.calibrate)
            self.calibrate_button.setFont(button_font)
            self.calibrate_button.setStyleSheet("background-color: Ivory;")
            grid.addWidget(self.calibrate_button, 1, 3)

            # Aiming
            calibrater_widget = QWidget()
            calibrater_layout = QVBoxLayout()
            self.calibrater_image = QLabel()
            pixmap = QPixmap(r"C:\Users\Wang_glove box\Desktop\Transfer Controller\calibrator.png")
            self.calibrater_image.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            self.calibrater_image.mousePressEvent = self.aim
            calibrater_layout.addWidget(self.calibrater_image, alignment=Qt.AlignCenter)
            calibrater_widget.setLayout(calibrater_layout)
            grid.addWidget(calibrater_widget, 3, 1)

            # Align Polygon
            self.align_button = QPushButton('Track Flake')
            self.align_button.pressed.connect(self.align)
            self.align_button.setFont(button_font)
            self.align_button.setStyleSheet("background-color: Ivory;")
            grid.addWidget(self.align_button, 2, 3)

            # Turn on/off alignment
            self.light_button = QPushButton()
            self.light_button.setCheckable(True)
            self.light_button.toggled.connect(self.light_action)
            self.light_button.setFont(button_font)
            self.light_button.setStyleSheet("""
                QPushButton {
                    background-color: red;
                    border-style: solid;
                    border-width: 15px;
                    border-radius: 25px;
                    min-width: 20px;
                    max-width: 20px;
                    min-height: 20px;
                    max-height: 20px;
                }
                QPushButton:checked {
                    background-color: green;
                }
            """)
            # create a layout and add the light_button to it
            light_button_layout = QVBoxLayout()
            light_button_layout.addWidget(self.light_button)
            # add the layout to the grid
            grid.addLayout(light_button_layout, 2, 4)

            # Transfer
            self.transfer_button = QPushButton('Transfer')
            self.transfer_button.pressed.connect(self.transfer)
            self.transfer_button.setFont(big_button_font)
            self.transfer_button.setFixedSize(big_button_size, 80)
            self.transfer_button.setStyleSheet("background-color: Green;")
            grid.addWidget(self.transfer_button, 3, 3)

            self.worker = Transfer()
            self.worker.subThread1.log_signal.connect(self.append_analysis_log)
            # self.worker.subThread1.request_reference_image.connect(self.prompt_reference_image)
            self.worker.subThread1.request_stamp_install.connect(self.prompt_stamp_install)
            self.worker.subThread1.focus_score_signal.connect(self.update_focus_score_plot)


            # PPC/PET method
            self.method = "PC"
            self.method_button = QPushButton("PC")
            self.method_button.clicked.connect(self.switch_method)
            grid.addWidget(self.method_button, 3, 4)


        # Create frames for devices
        else:

            # Device label
            if self.device_channel is None:  # For CC devices
                device_label = QLabel(f"Device KDC-{self.device_serial_num.value.decode()}", self)
            if self.device_channel is not None:  # For KIM devices
                device_label = QLabel(
                    f"Device KIM-{self.device_serial_num.value.decode()}-Channel {self.device_channel}",
                    self)
            font = QFont("Arial")
            font.setPointSize(8)
            device_label.setFont(font)
            grid.addWidget(device_label, 0, 0)

            # Device status
            self.status_label = QLabel("", self)
            font = QFont("Arial")
            font.setPointSize(12)
            self.status_label.setFont(font)
            grid.addWidget(self.status_label, 1, 0)

            # Device current position
            self.position_label = QLabel("", self)
            grid.addWidget(self.position_label, 2, 0)

            # Define a grid layout for the choices frame
            self.choices_frame = QFrame(self)
            grid.addWidget(self.choices_frame, 3, 0, 1, 2)

            choices_grid = QGridLayout(self.choices_frame)
            self.choices_frame.setLayout(choices_grid)
            self.choices_frame.hide()

            self.show_hide_button = QPushButton("Choices", self)
            self.show_hide_button.setFont(button_font)
            self.show_hide_button.setStyleSheet("background-color: silver;")
            grid.addWidget(self.show_hide_button, 1, 1)
            self.show_hide_button.clicked.connect(self.show_hide_choices)

            # Connect all devices initially
            self.connect_and_show_choices()

            if self.device_channel is None:  # For CC devices

                self.step_label = QLabel("Step", self.choices_frame)
                self.step_label.setFont(label_font)
                self.step_label.setStyleSheet("background-color: lightgray;")
                choices_grid.addWidget(self.step_label, 0, 5)

                self.step_entry = QLineEdit(self.choices_frame)
                self.step_entry.setValidator(QDoubleValidator())
                self.step_entry.setText("10000" if self.device_name == "Sample Stage Rotator" else "5000")
                choices_grid.addWidget(self.step_entry, 0, 6)

                self.velocity_label = QLabel("Velocity", self.choices_frame)
                self.velocity_label.setFont(label_font)
                self.velocity_label.setStyleSheet("background-color: lightgray;")
                choices_grid.addWidget(self.velocity_label, 1, 5)

                self.velocity_entry = QLineEdit(self.choices_frame)
                self.velocity_entry.setValidator(QDoubleValidator())
                self.velocity_entry.setText("1000")
                choices_grid.addWidget(self.velocity_entry, 1, 6)

            else:  # For KIM devices

                # Coarse settings
                self.coarse_frame = QFrame(self.choices_frame)
                self.coarse_frame.setFrameShape(QFrame.StyledPanel)
                self.coarse_frame.setFrameShadow(QFrame.Raised)
                self.coarse_frame.setStyleSheet("border: 1px solid black;")

                coarse_frame_grid = QGridLayout(self.coarse_frame)

                self.bigstep_label = QLabel("STEP", self.coarse_frame)
                self.bigstep_label.setFont(label_font)
                self.bigstep_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigstep_label, 0, 0)

                self.bigstep_entry = QLineEdit(self.coarse_frame)
                self.bigstep_entry.setValidator(QDoubleValidator())
                self.bigstep_entry.setText("1000")
                coarse_frame_grid.addWidget(self.bigstep_entry, 0, 1)

                self.bigrate_label = QLabel("RATE", self.coarse_frame)
                self.bigrate_label.setFont(label_font)
                self.bigrate_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigrate_label, 1, 0)

                self.bigrate_entry = QLineEdit(self.coarse_frame)
                self.bigrate_entry.setValidator(QDoubleValidator())
                self.bigrate_entry.setText("1000")
                coarse_frame_grid.addWidget(self.bigrate_entry, 1, 1)

                self.bigacceleration_label = QLabel("ACCE", self.coarse_frame)
                self.bigacceleration_label.setFont(label_font)
                self.bigacceleration_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigacceleration_label, 0, 2)

                self.bigacceleration_entry = QLineEdit(self.coarse_frame)
                self.bigacceleration_entry.setValidator(QDoubleValidator())
                self.bigacceleration_entry.setText("10000")
                coarse_frame_grid.addWidget(self.bigacceleration_entry, 0, 3)

                self.bigvoltage_label = QLabel("VOLT", self.coarse_frame)
                self.bigvoltage_label.setFont(label_font)
                self.bigvoltage_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigvoltage_label, 1, 2)

                self.bigvoltage_entry = QLineEdit(self.coarse_frame)
                self.bigvoltage_entry.setValidator(QDoubleValidator())
                self.bigvoltage_entry.setText("1000")
                coarse_frame_grid.addWidget(self.bigvoltage_entry, 1, 3)

                # Add the sub-frame to the existing grid layout
                choices_grid.addWidget(self.coarse_frame, 0, 5, 2, 5)  # Adjust grid position as needed

                # Fine settings
                self.fine_frame = QFrame(self.choices_frame)
                self.fine_frame.setFrameShape(QFrame.StyledPanel)
                self.fine_frame.setFrameShadow(QFrame.Raised)
                self.fine_frame.setStyleSheet("border: 1px solid black;")

                fine_frame_grid = QGridLayout(self.fine_frame)

                self.smallstep_label = QLabel("step", self.fine_frame)
                self.smallstep_label.setFont(label_font)
                self.smallstep_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallstep_label, 0, 0)

                self.smallstep_entry = QLineEdit(self.fine_frame)
                self.smallstep_entry.setValidator(QDoubleValidator())
                self.smallstep_entry.setText("100")
                fine_frame_grid.addWidget(self.smallstep_entry, 0, 1)

                self.smallrate_label = QLabel("rate", self.fine_frame)
                self.smallrate_label.setFont(label_font)
                self.smallrate_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallrate_label, 1, 0)

                self.smallrate_entry = QLineEdit(self.fine_frame)
                self.smallrate_entry.setValidator(QDoubleValidator())
                self.smallrate_entry.setText("100")
                fine_frame_grid.addWidget(self.smallrate_entry, 1, 1)

                self.smallacceleration_label = QLabel("acce", self.fine_frame)
                self.smallacceleration_label.setFont(label_font)
                self.smallacceleration_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallacceleration_label, 0, 2)

                self.smallacceleration_entry = QLineEdit(self.fine_frame)
                self.smallacceleration_entry.setValidator(QDoubleValidator())
                self.smallacceleration_entry.setText("10000")
                fine_frame_grid.addWidget(self.smallacceleration_entry, 0, 3)

                self.smallvoltage_label = QLabel("volt", self.fine_frame)
                self.smallvoltage_label.setFont(label_font)
                self.smallvoltage_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallvoltage_label, 1, 2)

                self.smallvoltage_entry = QLineEdit(self.fine_frame)
                self.smallvoltage_entry.setValidator(QDoubleValidator())
                self.smallvoltage_entry.setText("1000")
                fine_frame_grid.addWidget(self.smallvoltage_entry, 1, 3)

                choices_grid.addWidget(self.fine_frame, 0, 10, 2, 5)  # Adjust grid position as needed

                # Jod/continuous mode
                self.mode = "Jog"
                self.jogmode_button = QPushButton("Jog", self.choices_frame)
                self.jogmode_button.clicked.connect(self.switch_jogmode)
                # self.jogmode_button.resize(self.jogmode_button.sizeHint())
                # self.jogmode_button.move(50, 50)
                choices_grid.addWidget(self.jogmode_button, 1, 15)

            connect_button = QPushButton("Connect", self.choices_frame)
            connect_button.setFont(button_font)
            connect_button.setStyleSheet("background-color: HoneyDew;")
            connect_button.clicked.connect(self.connect_device)
            grid.addWidget(connect_button, 0, 1)

            disconnect_button = QPushButton("Disconnect", self.choices_frame)
            disconnect_button.setFont(button_font)
            disconnect_button.setStyleSheet("color: white; background-color: maroon;")
            disconnect_button.clicked.connect(self.disconnect_device)
            grid.addWidget(disconnect_button, 2, 1)

            home_button = QPushButton("Home", self.choices_frame)
            home_button.setFont(button_font)
            home_button.setStyleSheet("background-color: gold;")
            home_button.clicked.connect(self.home_device)
            choices_grid.addWidget(home_button, 1, 2)

            if self.device_channel is None:  # For CC devices
                drive_positive_button = QPushButton("Drive +", self.choices_frame)
                drive_positive_button.setFont(button_font)
                drive_positive_button.setStyleSheet("background-color: Ivory;")
                drive_positive_button.clicked.connect(lambda: self.drive_CCdevice('right'))
                choices_grid.addWidget(drive_positive_button, 0, 2)

                drive_negative_button = QPushButton("Drive -", self.choices_frame)
                drive_negative_button.setFont(button_font)
                drive_negative_button.setStyleSheet("background-color: Ivory;")
                drive_negative_button.clicked.connect(lambda: self.drive_CCdevice('left'))
                choices_grid.addWidget(drive_negative_button, 2, 2)

            else:  # For KIM devices
                drive_positive_button = QPushButton("Drive +", self.choices_frame)
                drive_positive_button.setFont(button_font)
                drive_positive_button.setStyleSheet("background-color: Ivory;")
                drive_positive_button.clicked.connect(lambda: self.drive_KIMdevice(True))
                choices_grid.addWidget(drive_positive_button, 0, 2)

                drive_negative_button = QPushButton("Drive -", self.choices_frame)
                drive_negative_button.setFont(button_font)
                drive_negative_button.setStyleSheet("background-color: Ivory;")
                drive_negative_button.clicked.connect(lambda: self.drive_KIMdevice(False))
                choices_grid.addWidget(drive_negative_button, 2, 2)

            stop_button = QPushButton("Stop", self.choices_frame)
            stop_button.setFont(button_font)
            stop_button.setStyleSheet("color: white; background-color: firebrick;")
            stop_button.clicked.connect(self.stop_device)
            choices_grid.addWidget(stop_button, 1, 4)

            if self.device_channel is None:  # For CC devices
                if self.device_name != "Sample Stage Rotator":
                    move_positive_button = QPushButton("Move +", self.choices_frame)
                    move_positive_button.setFont(button_font)
                    move_positive_button.setStyleSheet("background-color: Ivory;")
                    move_positive_button.clicked.connect(lambda: self.move_CCdevice(True))
                    choices_grid.addWidget(move_positive_button, 0, 4)

                    move_negative_button = QPushButton("Move -", self.choices_frame)
                    move_negative_button.setFont(button_font)
                    move_negative_button.setStyleSheet("background-color: Ivory;")
                    move_negative_button.clicked.connect(lambda: self.move_CCdevice(False))
                    choices_grid.addWidget(move_negative_button, 2, 4)

                if self.device_name == "Sample Stage Rotator":
                    rotate_positive_button = QPushButton("Rotate +", self.choices_frame)
                    rotate_positive_button.setFont(button_font)
                    rotate_positive_button.setStyleSheet("background-color: Ivory;")
                    rotate_positive_button.clicked.connect(lambda: self.move_CCdevice(True))
                    choices_grid.addWidget(rotate_positive_button, 0, 4)

                    rotate_negative_button = QPushButton("Rotate -", self.choices_frame)
                    rotate_negative_button.setFont(button_font)
                    rotate_negative_button.setStyleSheet("background-color: Ivory;")
                    rotate_negative_button.clicked.connect(lambda: self.move_CCdevice(False))
                    choices_grid.addWidget(rotate_negative_button, 2, 4)

            else:  # For KIM devices
                move_positive_button = QPushButton("Move +", self.choices_frame)
                move_positive_button.setFont(button_font)
                move_positive_button.setStyleSheet("background-color: Ivory;")
                move_positive_button.clicked.connect(lambda: self.move_KIMdevice(True))
                choices_grid.addWidget(move_positive_button, 0, 4)

                move_negative_button = QPushButton("Move -", self.choices_frame)
                move_negative_button.setFont(button_font)
                move_negative_button.setStyleSheet("background-color: Ivory;")
                move_negative_button.clicked.connect(lambda: self.move_KIMdevice(False))
                choices_grid.addWidget(move_negative_button, 2, 4)

            if self.device_channel is None:  # For CC devices
                apply_button = QPushButton("Apply Parameters", self.choices_frame)
                apply_button.setFont(button_font)
                apply_button.setStyleSheet("background-color: tan;")
                apply_button.clicked.connect(self.apply_parameters)
                choices_grid.addWidget(apply_button, 1, 9)
            else:  # For KIM devices
                apply_bigbutton = QPushButton("Apply Coarse Parameters", self.choices_frame)
                apply_bigbutton.setFont(button_font)
                apply_bigbutton.setStyleSheet("background-color: tan;")
                apply_bigbutton.clicked.connect(self.apply_bigparameters)
                choices_grid.addWidget(apply_bigbutton, 2, 7)

                apply_smallbutton = QPushButton("Apply Fine Parameters", self.choices_frame)
                apply_smallbutton.setFont(button_font)
                apply_smallbutton.setStyleSheet("background-color: tan;")
                apply_smallbutton.clicked.connect(self.apply_smallparameters)
                choices_grid.addWidget(apply_smallbutton, 2, 12)

            self.choices_frame.setVisible(False)  # Hide the frame initially

    """------------------------------------------------------------------------------------"""
    # B. Camera functions

    def open_camera(self):
        try:
            if hasattr(self, "camera_thread") and self.camera_thread is not None:
                if self.camera_thread.isRunning():
                    print("Stopping existing camera thread...")
                    self.camera_thread.stop()
                    self.camera_thread.wait()
                    print("Previous camera thread stopped.")
                self.camera_thread = None

            print("Starting new camera thread...")
            self.camera_thread = CameraThread()
            g.camera_thread = self.camera_thread

            # Check camera_widget is initialized
            if not hasattr(self, "camera_widget") or self.camera_widget is None:
                self.camera_widget = CameraWidget()

            self.camera_thread.frame_ready.connect(self.camera_widget.update_image)
            self.camera_thread.start()

            self.status_label.setText("Camera connected successfully.")
            self.camera_widget.show()

        except Exception as e:
            import traceback
            print("Exception in open_camera:", e)
            traceback.print_exc()

    def capture(self):
        status_message = capture_frame(g.frame)
        self.update_status(status_message)

    # Trigger tracking mode
    def trigger_mode1(self, event):
        status_message = "Continue tracking..."
        self.update_status(status_message)
        g.mode = "tracking"

    # Trigger drawing mode
    def trigger_mode2(self, event):
        status_message = "Start design a device..."
        self.update_status(status_message)
        g.mode = "drawing"

    # Trigger measuring mode
    def trigger_mode3(self, event):
        status_message = "Measuring..."
        self.update_status(status_message)
        g.mode = "measuring"

    # Set up a set point for co-rotation
    def aim(self, event):
        status_message = "Setting up a set point..."
        self.update_status(status_message)

        old_polygon_profile = get_polygon()
        old_center = old_polygon_profile["center"]
        g.center = old_center

        step_r = 150000
        velocity_r = 10

        print(move_CCdevice(self.device_profile["servo"][3], "servo", None, True, abs(step_r),
                            velocity_r))

        time.sleep(1)
        status_message = "Rotate back..."
        self.update_status(status_message)

        new_polygon_profile = get_polygon()
        new_center = new_polygon_profile["center"]

        if old_center and new_center is not None:
            radius, theta = solve_for_r(old_center[0], old_center[1], new_center[0], new_center[1], -1 * np.pi / 180)
            g.radius = radius
            time.sleep(1)
            print((new_center[0] - old_center[0], new_center[1] - old_center[1]))

            print(move_CCdevice(self.device_profile["servo"][3], "servo", None, False, abs(step_r),
                                velocity_r))

            g.origin_coordinate = (old_center[0] - radius * np.cos(theta), old_center[1] - radius * np.sin(theta))

            success_dialog = QMessageBox()
            success_dialog.setWindowTitle("Set point")
            success_dialog.setText(f"Radius: {g.radius}; Rotation center: {g.origin_coordinate}")
            success_dialog.exec_()

            status_message = "Set point set."
            self.update_status(status_message)
        else:
            error_dialog = QMessageBox()
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("Please Select a target first.")
            error_dialog.exec_()

    def zoom_in(self):
        zoom_in_camera()

    def zoom_out(self):
        zoom_out_camera()

    def fivefold(self):

        g.parameters["Camera"]["Rescale"] = (25580, 19400)
        g.parameters["Camera"]["Scalebar"] = 500
        status_message = "5X Microscope"
        self.update_status(status_message)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Conversion Size")
        success_dialog.setText(f"Conversion size: {g.parameters['Camera']['Rescale']}")
        success_dialog.exec_()

    def tenfold(self):

        g.parameters["Camera"]["Rescale"] = (25580 / 2, 19400 / 2)
        g.parameters["Camera"]["Scalebar"] = 250
        status_message = "10X Microscope"
        self.update_status(status_message)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Conversion Size")
        success_dialog.setText(f"Conversion size: {g.parameters['Camera']['Rescale']}")
        success_dialog.exec_()

    def twentyfold(self):

        g.parameters["Camera"]["Rescale"] = (25580 / 4, 19400 / 4)
        g.parameters["Camera"]["Scalebar"] = 125
        status_message = "20X Microscope"
        self.update_status(status_message)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Conversion Size")
        success_dialog.setText(f"Conversion size: {g.parameters['Camera']['Rescale']}")
        success_dialog.exec_()

    def retrieve_polygon(self):
        status_message = "Retrieving flake profile..."
        self.update_status(status_message)

        polygon_profile = get_polygon()
        formatted_profile = json.dumps(polygon_profile, indent=4, default=str)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Flake Profile")
        success_dialog.setText(f"Flake profile: \n{formatted_profile}")
        success_dialog.exec_()

        status_message = "Retrieved."
        self.update_status(status_message)

    def calibrate(self):

        status_message = "Calibrating flake..."
        self.update_status(status_message)

        # Calculate conversion factors
        device_steps_per_view_x = g.parameters["Camera"]["Rescale"][0] / (
                g.parameters["Sample Stage X-Axis"]["CCstep"] / 5000)  # full device x movement
        device_steps_per_view_y = g.parameters["Camera"]["Rescale"][1] / (
                g.parameters["Sample Stage Y-Axis"]["CCstep"] / 5000)  # full device y movement
        camera_pixels_per_view_x = 640  # full width of the camera image
        camera_pixels_per_view_y = 480  # full height of the camera image
        camera_center = (g.original_frame_width / 2, g.original_frame_height / 2)

        conversion_factor_x = device_steps_per_view_x / camera_pixels_per_view_x
        conversion_factor_y = device_steps_per_view_y / camera_pixels_per_view_y

        polygon_profile = get_polygon()
        polygon_center = polygon_profile["center"]

        if polygon_center is not None:

            shift_vector = (camera_center[0] - polygon_center[0], camera_center[1] - polygon_center[1])

            success_dialog = QMessageBox()
            success_dialog.setWindowTitle("Calibration")
            success_dialog.setText(f"Shift_vector: {shift_vector}")
            success_dialog.exec_()

            # Convert shift vector to device steps
            shift_vector_device = (int(shift_vector[0] * conversion_factor_x), int(shift_vector[1] * conversion_factor_y))

            step_x = int(shift_vector_device[0])
            velocity_x = 100
            if step_x >= 0:
                direction_x = False
            else:
                direction_x = True

            print(move_CCdevice(self.device_profile["servo"][1], "servo", None, direction_x, abs(step_x),
                                velocity_x))

            step_y = -int(shift_vector_device[1])
            velocity_y = 100
            if step_y >= 0:
                direction_y = False
            else:
                direction_y = True

            print(move_CCdevice(self.device_profile["servo"][2], "servo", None, direction_y, abs(step_y),
                                velocity_y))

            status_message = "Calibrated."
            self.update_status(status_message)
        else:
            status_message = "No flake is selected."
            self.update_status(status_message)
    
    def align(self):
        if self.align_button.text() == "Align Flake":
            self.alignment_running = True
            self.align_button.setText("Stop")
            self.status_label.setText("Aligning flake...")

            # Call alignment in main thread (will block GUI unless we process events)
            self.autoalignment()

        else:
            # Stop button pressed
            self.alignment_running = False
            self.align_button.setText("Align Flake")
            self.status_label.setText("Alignment stopped.")
            self.stop_all_motors()
    
    def stop_all_motors(self):
        try:
            print("🔴 Force stopping all motors...")
            stop_device(self.device_profile["servo"][1], "servo", None)  # X
            stop_device(self.device_profile["servo"][2], "servo", None)  # Y
            stop_device(self.device_profile["servo"][3], "servo", None)  # Rotation
        except Exception as e:
            print("⚠️ Error in stop_all_motors():", e)

    def autoalignment(self):
        try:
            self.update_status("Aligning flake...")
            shift_vector = get_shift()
            rotate_angle = get_angle()

            # Show shift and angle
            QMessageBox.information(None, "Alignment",
                                    f"Shift_vector: {shift_vector}, Rotate angle: {rotate_angle}")

            # --- Conversion Factors ---
            p = g.parameters
            device_steps_per_view_x = p["Camera"]["Rescale"][0] / (p["Sample Stage X-Axis"]["CCstep"] / 500)
            device_steps_per_view_y = p["Camera"]["Rescale"][1] / (p["Sample Stage Y-Axis"]["CCstep"] / 500)
            conversion_factor_x = device_steps_per_view_x / 640
            conversion_factor_y = device_steps_per_view_y / 480
            conversion_factor_rotate = 150000 / (p["Sample Stage Rotator"]["CCstep"] / 1000)

            # --- Old rotation calibration codes ---
            # cal_x = cal_y = 0
            # if g.origin_coordinate:
            #     align_center = get_polygon()["center"]
            #     dx, dy = align_center[0] - g.origin_coordinate[0], align_center[1] - g.origin_coordinate[1]
            #     radius = np.hypot(dx, dy)
            #     theta = np.arctan2(dy, dx)
            #     cal_x = radius * (np.cos(theta - np.radians(1)) - np.cos(theta)) * conversion_factor_x
            #     cal_y = radius * (np.sin(theta - np.radians(1)) - np.sin(theta)) * conversion_factor_y

            # # --- Motion Parameters ---
            # small_angle = 1
            # move_config = {
            #     "rotate": {
            #         "angle": rotate_angle,
            #         "direction": rotate_angle < 0,
            #         "step": lambda: int(small_angle * conversion_factor_rotate),
            #         "servo_id": 3,
            #         "value": 0,
            #         "velocity": 10,
            #         "loops": lambda: int(abs(rotate_angle))
            #     },
            #     "cal_x": {
            #         "angle": rotate_angle,
            #         "direction": cal_x < 0,
            #         "step": lambda: abs(int(cal_x)),
            #         "servo_id": 1,
            #         "value": cal_x,
            #         "velocity": 10,
            #         "loops": lambda: int(abs(rotate_angle))
            #     },
            #     "cal_y": {
            #         "angle": rotate_angle,
            #         "direction": cal_y < 0,
            #         "step": lambda: abs(int(cal_y)),
            #         "servo_id": 2,
            #         "value": cal_y,
            #         "velocity": 10,
            #         "loops": lambda: int(abs(rotate_angle))
            #     }
            # }

            # def run_motion(label):
            #     cfg = move_config[label]
            #     for _ in range(cfg["loops"]()):
            #         if not self.alignment_running:
            #             print(f"🛑 Alignment stopped during {label}")
            #             return
            #         print(cfg["value"])
            #         move_CCdevice(self.device_profile["servo"][cfg["servo_id"]], "servo", None,
            #                     cfg["direction"], -cfg["step"](), cfg["velocity"])
            #         time.sleep(0.5)
            #         QApplication.processEvents()

            # # --- Execute motions sequentially ---
            # for key in ["rotate", "cal_x", "cal_y"]:
            #     run_motion(key)
            
            # self.log("=== Starting Incremental Rotation with XY Realignment ===")
            self.run_rotation_with_tracking(
                rotate_angle,
                conversion_factor_rotate,
                conversion_factor_x,
                conversion_factor_y
            )
            # --- Shift in X/Y ---
            origin = get_polygon_tracker()["center"]
            target = get_polygon()["center"]
            shift_device = (
                shift_vector[0] * conversion_factor_x,
                shift_vector[1] * conversion_factor_y
            )

            def shift_axis(index, value, velocity):
                step = 1000
                num = int(value // step)
                res = value % step
                direction = value < 0
                rdirection = res < 0

                for _ in range(abs(num)):
                    if not self.alignment_running:
                        print("🛑 Alignment stopped during shift")
                        return
                    move_CCdevice(self.device_profile["servo"][index], "servo", None,
                                direction, abs(step), velocity)
                    time.sleep(0.5)
                    QApplication.processEvents()

                if abs(res) > 0:
                    move_CCdevice(self.device_profile["servo"][index], "servo", None,
                                rdirection, abs(round(res)), velocity)
                    time.sleep(0.5)
                    QApplication.processEvents()

            shift_axis(1, shift_device[0], 500)
            shift_axis(2, -shift_device[1], 500)

            # --- PID Tuning ---
            aim_x, aim_y = target
            error_x = error_y = 100
            prev_error_x = prev_error_y = 0
            integral_x = integral_y = 0
            iteration = 0
            threshold_error = 1
            max_iterations = 20

            while (abs(error_x) > threshold_error or abs(error_y) > threshold_error) and iteration < max_iterations:
                if not self.alignment_running:
                    print("🛑 Alignment stopped during PID")
                    return

                center = get_polygon_tracker()["center"]
                current_error_x, current_error_y = center[0] - aim_x, center[1] - aim_y
                error_mag = np.hypot(current_error_x, current_error_y)

                # Choose PID profile
                if error_mag > 100:
                    Kp, Ki, Kd = 1.0, 0.02, 0.05
                elif error_mag > 20:
                    Kp, Ki, Kd = 0.6, 0.05, 0.05
                else:
                    Kp, Ki, Kd = 0.4, 0.1, 0.01

                # PID math
                integral_x += current_error_x
                integral_y += current_error_y
                derivative_x = current_error_x - prev_error_x
                derivative_y = current_error_y - prev_error_y

                output_x = Kp * current_error_x + Ki * integral_x + Kd * derivative_x
                output_y = Kp * current_error_y + Ki * integral_y + Kd * derivative_y

                direction_x = output_x > 0
                direction_y = output_y < 0
                step_x = abs(round(output_x))
                step_y = abs(round(output_y))

                if step_x > 0:
                    move_CCdevice(self.device_profile["servo"][1], "servo", None,
                                direction_x, step_x, 500)
                if step_y > 0:
                    move_CCdevice(self.device_profile["servo"][2], "servo", None,
                                direction_y, step_y, 500)

                prev_error_x = current_error_x
                prev_error_y = current_error_y
                error_x = current_error_x
                error_y = current_error_y

                iteration += 1
                time.sleep(0.3)
                QApplication.processEvents()

            # --- Final Status ---
            if iteration >= max_iterations:
                self.update_status("Max PID iterations reached. Alignment may be incomplete.")
            else:
                self.update_status("Aligned.")

            self.status_label.setText("✅ Alignment complete.")
            self.align_button.setText("Align Flake")
            self.alignment_running = False

        except Exception as e:
            print("❌ Alignment error:", e)
            self.status_label.setText(f"❌ Alignment failed: {e}")
            self.align_button.setText("Align Flake")
            self.alignment_running = False

    def run_rotation_with_tracking(self, rotate_angle, conversion_factor_rotate, conversion_factor_x, conversion_factor_y):
        """
        Rotate by 1° increments. After each, correct the XY offset to bring the object back to the original center.
        """
        small_angle = 1
        total_steps = int(abs(rotate_angle))
        direction = rotate_angle > 0  # Clockwise = True

        original_center = get_polygon()["center"]

        for step in range(total_steps):
            if not self.alignment_running:
                print("🛑 Alignment stopped.")
                return

            # Step 1: Rotate by 1°
            rotate_step = int(small_angle * conversion_factor_rotate)
            move_CCdevice(self.device_profile["servo"][3], "servo", None,
                        direction, -rotate_step, 10)
            time.sleep(0.5)
            QApplication.processEvents()

            # Step 2: Track new center
            new_center = get_polygon()["center"]
            dx = new_center[0] - original_center[0]
            dy = new_center[1] - original_center[1]

            # Convert shift to device step units
            move_x = int(dx * conversion_factor_x)
            move_y = int(dy * conversion_factor_y)

            # Step 3: Correct X
            if move_x != 0:
                move_CCdevice(self.device_profile["servo"][1], "servo", None,
                            move_x < 0, abs(move_x), 10)
                time.sleep(0.3)
                QApplication.processEvents()

            # Step 4: Correct Y
            if move_y != 0:
                move_CCdevice(self.device_profile["servo"][2], "servo", None,
                            move_y < 0, abs(move_y), 10)
                time.sleep(0.3)
                QApplication.processEvents()

            # self.log(f"[Rotation Step {step + 1}/{total_steps}] dx={dx:.2f}, dy={dy:.2f}, move_x={move_x}, move_y={move_y}")


    def light_action(self, checked):
        if checked:
            # light is on, trigger action A
            g.disaligning = False
            self.align_button.setText("Align Flake")
            status_message = "Start aligning..."
            self.update_status(status_message)
        else:
            # light is off, trigger action B
            g.disaligning = True
            self.align_button.setText("Track Flake")
            status_message = "Continue tracking..."
            self.update_status(status_message)
    
    def transfer(self):
        print("🔷 transfer() called")
        self.add_transfer_analysis_ui()
        if hasattr(self, 'focus_plot'):
            self.focus_plot.reset()
        self.worker.start()
            
    def switch_method(self):

        if self.method == "PC":
            self.method = "PET"
            self.method_button.setText("PET")
            pass
            status_message = "PET transfer"
        else:
            self.method = "PC"
            self.method_button.setText("PC")
            pass
            status_message = "PPC transfer"
        self.update_status(status_message)

    """------------------------------------------------------------------------------------"""
    # C. Machine functions
    # Implement connect, disconnect, stop, move, drive, update current position, etc. commands for Thorlab devices

    def connect_and_show_choices(self):
        self.connect_device()
        # Clear the stop event and start a new thread to update the position
        # self.stop_position_update_event.clear()
        # position_update_thread = threading.Thread(target=self.update_position_in_background)
        # position_update_thread.start()
        # self.update_position_label_from_queue()

    def show_hide_choices(self):
        if self.choices_frame.isVisible():
            self.choices_frame.setVisible(False)
            self.show_hide_button.setText("Choices")
        else:
            self.choices_frame.setVisible(True)
            self.show_hide_button.setText("Hide")

    def update_position_in_background(self):
        while not self.stop_position_update_event.is_set():
            connection_status, _ = is_connected(self.device_serial_num, self.device_type, self.device_channel)
            if connection_status:
                position = get_current_position(self.device_serial_num, self.device_type, self.device_channel)
                self.position_queue.put(position)
            time.sleep(0.1)  # Poll every 100 ms

    def update_position_label_from_queue(self):
        try:
            position = self.position_queue.get_nowait()
            self.position_label.config(text=f"{position}")
        except Empty:
            pass
        finally:
            if not self.stop_position_update_event.is_set():
                self.position_label.after(100, self.update_position_label_from_queue)

    def connect_device(self):
        status_message = connect_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)

    def disconnect_device(self):
        status_message = disconnect_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)

    def home_device(self):
        status_message = home_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)

    def move_CCdevice(self, direction):
        step = int(self.step_entry.text())
        velocity = int(self.velocity_entry.text())
        status_message = move_CCdevice(self.device_serial_num, self.device_type, self.device_channel, direction, step,
                                       velocity)
        self.update_status(status_message)

    def move_KIMdevice(self, direction):

        step = int(g.parameters[self.device_name]["KIMstep"])
        rate = int(g.parameters[self.device_name]["KIMrate"])
        acceleration = int(g.parameters[self.device_name]["KIMacceleration"])

        mode = int(g.parameters[self.device_name]["KIMjogmode"])
        status_message = move_KIMdevice(self.device_serial_num, self.device_type, self.device_channel, direction, step,
                                        rate, acceleration, mode)
        self.update_status(status_message)

    def drive_CCdevice(self, direction):
        # velocity =
        # Start driving the device in a new thread
        step = int(self.step_entry.text())
        velocity = int(self.velocity_entry.text())
        status_message = self.device_CCdriver.start_drive(self.device_serial_num, self.device_type, self.device_channel,
                                                          direction, step, velocity)
        self.update_status(status_message)

    def drive_KIMdevice(self, direction):
        # velocity =
        # Start driving the device in a new thread
        voltage = int(g.parameters[self.device_name]["KIMvoltage"])
        rate = int(g.parameters[self.device_name]["KIMrate"])
        acceleration = int(g.parameters[self.device_name]["KIMacceleration"])
        status_message = drive_KIMdevice(self.device_serial_num, self.device_type, self.device_channel, direction,
                                         voltage, rate, acceleration)
        self.update_status(status_message)

    def stop_device(self):
        # This will stop the 'drive_device' thread if it is running
        if self.device_channel is None:
            self.device_CCdriver.stop_drive()
        else:
            stop_device(self.device_serial_num, self.device_type, self.device_channel)

        # This will stop the movement of the device
        status_message = stop_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)
        # joystick_state[self.device_name][1] = False

    def switch_jogmode(self):

        if self.mode == "Jog":
            self.mode = "Continuous"
            self.jogmode_button.setText("Continuous")
            g.parameters[self.device_name]["KIMjogmode"] = 1  # Function for Continuous mode
            status_message = "Continuous mode"
        else:
            self.mode = "Jog"
            self.jogmode_button.setText("Jog")
            g.parameters[self.device_name]["KIMjogmode"] = 2  # Function for Jog mode
            status_message = "Jog mode"
        self.update_status(status_message)

    def update_position_label(self):
        if self.device_channel is None:
            connection_status, _ = is_connected(self.device_serial_num, self.device_type, self.device_channel)
            if not connection_status:
                self.position_label.config(text=f"Device {self.device_serial_num.value.decode()} is not connected.")
            else:
                position = get_current_position(self.device_serial_num, self.device_type, self.device_channel)
                self.position_label.config(text=f"{position}")
                self.position_label.after(100, self.update_position_label)
        else:
            connection_status, _ = is_connected(self.device_serial_num, self.device_type, self.device_channel)
            if not connection_status:
                self.position_label.config(
                    text=f"Device {self.device_serial_num.value.decode()} Channel {self.device_channel} is not connected.")
            else:
                position = get_current_position(self.device_serial_num, self.device_type, self.device_channel)
                self.position_label.config(text=f"{position}")
                self.position_label.after(100, self.update_position_label)

    def apply_parameters(self):

        if self.device_channel is None:
            try:
                g.parameters[self.device_name]["CCstep"] = float(self.step_entry.text())
                g.parameters[self.device_name]["CCvelocity"] = float(self.velocity_entry.text())
            except ValueError:
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Invalid input")
                error_dialog.setText("Please enter valid numbers.")
                error_dialog.exec_()
                return

            status_message = set_CCstep(self.device_serial_num, self.device_type, self.device_channel,
                                        g.parameters[self.device_name]["CCstep"])
            self.update_status(status_message)

            set_CCvelocity(self.device_serial_num, self.device_type, self.device_channel,
                           g.parameters[self.device_name]["CCvelocity"])

            if status_message == f"Device {self.device_serial_num.value.decode()} is not connected.":
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Parameters")
                error_dialog.setText(f"Parameters for {self.device_name} failed to be updated")
                error_dialog.exec_()
            else:
                success_dialog = QMessageBox()
                success_dialog.setWindowTitle("Parameters")
                success_dialog.setText(f"Parameters for {self.device_name} updated successfully")
                success_dialog.exec_()

    def apply_bigparameters(self):

        if self.device_channel is not None:
            try:
                g.parameters[self.device_name]["KIMstep"] = float(self.bigstep_entry.text())
                g.parameters[self.device_name]["KIMrate"] = float(self.bigrate_entry.text())
                g.parameters[self.device_name]["KIMacceleration"] = float(self.bigacceleration_entry.text())
                g.parameters[self.device_name]["KIMvoltage"] = float(self.bigvoltage_entry.text())
            except ValueError:
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Invalid input")
                error_dialog.setText("Please enter valid numbers.")
                error_dialog.exec_()
                return

            status_message = set_KIMjog(self.device_serial_num, self.device_type, self.device_channel,
                                        g.parameters[self.device_name]["KIMjogmode"],
                                        g.parameters[self.device_name]["KIMstep"],
                                        g.parameters[self.device_name]["KIMstep"],
                                        g.parameters[self.device_name]["KIMrate"],
                                        g.parameters[self.device_name]["KIMacceleration"])
            self.update_status(status_message)

            if status_message == f"Device {self.device_serial_num.value.decode()} Channel {self.device_channel} is not connected.":
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Parameters")
                error_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} failed to be updated")
                error_dialog.exec_()
            else:
                success_dialog = QMessageBox()
                success_dialog.setWindowTitle("Parameters")
                success_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} updated successfully")
                success_dialog.exec_()

    def apply_smallparameters(self):

        if self.device_channel is not None:
            try:
                g.parameters[self.device_name]["KIMstep"] = float(self.smallstep_entry.text())
                g.parameters[self.device_name]["KIMrate"] = float(self.smallrate_entry.text())
                g.parameters[self.device_name]["KIMacceleration"] = float(self.smallacceleration_entry.text())
                g.parameters[self.device_name]["KIMvoltage"] = float(self.smallvoltage_entry.text())
            except ValueError:
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Invalid input")
                error_dialog.setText("Please enter valid numbers.")
                error_dialog.exec_()
                return

            status_message = set_KIMjog(self.device_serial_num, self.device_type, self.device_channel,
                                        g.parameters[self.device_name]["KIMjogmode"],
                                        g.parameters[self.device_name]["KIMstep"],
                                        g.parameters[self.device_name]["KIMstep"],
                                        g.parameters[self.device_name]["KIMrate"],
                                        g.parameters[self.device_name]["KIMacceleration"])
            self.update_status(status_message)

            if status_message == f"Device {self.device_serial_num.value.decode()} Channel {self.device_channel} is not connected.":
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Parameters")
                error_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} failed to be updated")
                error_dialog.exec_()
            else:
                success_dialog = QMessageBox()
                success_dialog.setWindowTitle("Parameters")
                success_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} updated successfully")
                success_dialog.exec_()
    
    def add_transfer_analysis_ui(self):
        # Prevent duplication if already added
        if hasattr(self, 'analysis_frame'):
            return

        # Get main grid layout
        main_layout = self.centralWidget().layout()

        # Create a vertical layout to hold both analysis and heater
        self.analysis_frame = QFrame()
        analysis_layout = QVBoxLayout()
        self.analysis_frame.setLayout(analysis_layout)

        # Style the analysis_frame
        self.analysis_frame.setFrameShape(QFrame.StyledPanel)
        self.analysis_frame.setStyleSheet("background-color: #f5f5f5; border: 1px solid gray;")

        # --- Heater Section ---
        self.heater_box = QGroupBox("Data")
        self.heater_box.setMinimumWidth(500)  # Set minimum width here
        heater_layout = QVBoxLayout()
        self.heater_box.setLayout(heater_layout)

        # Create temperature plot canvas
        self.focus_plot = FocusScorePlot()  # Change setpoint if needed
        heater_layout.addWidget(self.focus_plot)
        # self.worker.subThread2 = HeatingThread(setpoint=0.0)
        # print("[DEBUG] About to instantiate HeatingThread")
        # self.worker.subThread2.temp_signal.connect(self.temp_plot.update_temperature)
        # self.worker.subThread2.start()  # ✅ Start from GUI thread!

        # Add both sections to main analysis frame
        analysis_layout.addWidget(self.heater_box)

        # Add the analysis_frame to the layout at a new column index
        last_column = main_layout.columnCount()
        main_layout.addWidget(self.analysis_frame, 0, last_column, main_layout.rowCount(), 1)

    def prompt_reference_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Image", "", "Image Files (*.png *.jpg *.bmp)"
        )
        if file_path:
            self.worker.subThread1.set_reference_image(file_path)

    def prompt_stamp_install(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Install Stamp")
        msg.setText("Please install the stamp and press DONE when ready.")
        msg.setInformativeText("Click CANCEL to abort the transfer.")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.button(QMessageBox.Ok).setText("Done")
        msg.button(QMessageBox.Cancel).setText("Cancel")

        result = msg.exec_()
        if result == QMessageBox.Ok:
            self.worker.subThread1.user_stamp_response = True
        else:
            self.worker.subThread1.user_stamp_response = False
    
    def update_focus_score_plot(self, step_index, score):
        if hasattr(self, 'focus_plot'):
            self.focus_plot.update_score(step_index, score)


    def append_analysis_log(self, message):
        try:
            if hasattr(g, "image_analysis_log") and g.image_analysis_log:
                g.image_analysis_log.append(message)
                g.image_analysis_log.ensureCursorVisible()
        except Exception as e:
            print(f"[Log UI ERROR] {e}")

    def update_status(self, message):
        self.status_label.setText(message)


"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Transfer threads
class FocusingThread(QThread):
    log_signal = pyqtSignal(str)
    request_reference_image = pyqtSignal()
    reference_image_loaded = pyqtSignal(object)
    request_stamp_install = pyqtSignal()
    focus_score_signal = pyqtSignal(int, float)  # step index, score



    def __init__(self):

        super().__init__()
        self.reference_image = None
        self.user_stamp_response = None  # True for "Done", False for "Cancel"
    
    @QtCore.pyqtSlot(str)
    def set_reference_image(self, path):
        """Receives image path from main thread and loads it as grayscale."""
        if os.path.exists(path):
            image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if image is not None:
                self.reference_image = image
                self.log_signal.emit("Reference image loaded into thread.")
            else:
                self.log_signal.emit("❌ Failed to read image file.")
        else:
            self.log_signal.emit("❌ Invalid image path.")

    def run(self):
        """
        Focus algorithm:
        a) Coarse scan Z & capture frame at each step → compute focus metric
        b) Identify best focus plane
        c) Fine scan around that peak
        d) Repeat for stamp
        e) Move to sample best focus, then down to attach point
        f) Confirm focus convergence (difference minimized)
        """
        try:
            self.log = lambda msg: self.log_signal.emit(msg)
            self.log("Starting autofocus...")

            # ------------------- PARAMETERS -------------------
            focus_serial = c_char_p(b"27256526")
            stamp_serial = c_char_p(b"97100512")

            coarse_step = 2000      # µm equivalent device steps
            fine_step   = 500
            points_per_pass_coarse = 40   # sweep points
            points_per_pass_fine   = 5

            # ------------------- LOAD REFERENCE IMAGE -------------------

            # Ask main thread to show QFileDialog
            # self.log("Waiting for user to upload a reference image...")
            # self.request_reference_image.emit()

            # # Wait for main thread to respond (pause loop until image is set)
            # while self.reference_image is None:
            #     time.sleep(0.1)

            # # Use the image
            # g.reference_image = self.reference_image
            # self.log("Reference image loaded successfully. Proceeding to autofocus...")

            # autofocus loop: coarse + fine 
            def iterative_focus(
                focus_serial,
                coarse_step,
                coarse_points,
                fine_initial_step,
                label,
                ref_image,
                min_score_delta=0.5,
                max_fine_iterations=20
            ):
                """
                Coarse-to-fine focus optimizer with adaptive step size and directional control.
                Returns best focus index and detailed score history.
                """
                scores = []

                # --- 1. Coarse Sweep ---
                best_score = -1
                best_index = 0
                for i in range(coarse_points):
                    move_CCdevice(focus_serial, "servo", None, False, coarse_step, 3000)
                    time.sleep(0.5)

                    frame = g.frame
                    if frame is None:
                        score = 0
                        self.log(f"[{label} COARSE] step {i}: frame is None")
                    else:
                        # score = calculate_focus_similarity(frame, ref_image)
                        score = sobel_variance_focus_measure(frame)
                        self.focus_score_signal.emit(len(scores), score)


                    scores.append((score, i))
                    self.log(f"[{label} COARSE] step {i}: score = {score}")

                    if score > best_score:
                        best_score = score
                        best_index = i
                
                scores_arr = np.asarray(scores, dtype=float)   # shape (N, 2)
                score_only = scores_arr[:, 0]

                coarse_mu = score_only.mean()
                coarse_var = score_only.var(ddof=0)   # population variance
                print(f"mean={coarse_mu}, var={coarse_var}")
                
                reversed = 1
                if coarse_var <= 1000:
                    reversed = -reversed
                    self.log("Foco-plane is at the other side, reversing the direction...")
                    # Move back to zero before jumping to best coarse position
                    for _ in range(coarse_points):
                        move_CCdevice(focus_serial, "servo", None, True, coarse_step, 3000)
                        time.sleep(0.5)

                    new_scores = []
                    new_best_score = -1
                    new_best_index = 0
                    for i in range(coarse_points):
                        move_CCdevice(focus_serial, "servo", None, True, coarse_step, 3000)
                        time.sleep(0.5)

                        frame = g.frame
                        if frame is None:
                            new_score = 0
                            self.log(f"[{label} COARSE] step {i}: frame is None")
                        else:
                            # score = calculate_focus_similarity(frame, ref_image)
                            new_score = sobel_variance_focus_measure(frame)
                            self.focus_score_signal.emit(len(new_scores), new_score)


                        new_scores.append((new_score, i))
                        self.log(f"[{label} COARSE] step {i}: score = {new_score}")

                        if new_score > new_best_score:
                            new_best_score = new_score
                            new_best_index = i
                    
                    scores = new_scores
                    best_score = new_best_score
                    best_index = new_best_index
                    self.log(f"Best score={best_score}, now moving to best location={(best_index+1) * coarse_step}")

                    # Move back to zero before jumping to best coarse position
                    for _ in range(coarse_points-best_index):
                        move_CCdevice(focus_serial, "servo", None, False, coarse_step, 3000)
                        time.sleep(0.5)

                    # # Move to best coarse position
                    # move_CCdevice(focus_serial, "servo", None, True, (best_index+1) * coarse_step, 3000)
                    # time.sleep(0.2)

                elif coarse_var > 1000:
                    reversed = reversed
                    scores = scores
                    best_score = best_score
                    best_index = best_index
                
                    self.log(f"Best score={best_score}, now moving to best location={(best_index+1) * coarse_step}")

                    # Move back to zero before jumping to best coarse position
                    for _ in range(coarse_points-best_index):
                        move_CCdevice(focus_serial, "servo", None, True, coarse_step, 3000)
                        time.sleep(0.5)

                    # Move to best coarse position
                    # move_CCdevice(focus_serial, "servo", None, False, (best_index+1) * coarse_step, 3000)
                    # time.sleep(0.2)

                current_height = reversed*(best_index * coarse_step)

                self.log(f"Fine-tuning...")

                # --- 2. Fine Iterative Search ---
                current_score = best_score
                fine_step = fine_initial_step
                direction = True  # 1 = forward, -1 = backward
                fine_iterations = 0
                improvement = True

                while improvement and fine_iterations < max_fine_iterations:
                    move_CCdevice(focus_serial, "servo", None, direction == 1, fine_step, 500)
                    time.sleep(0.2)
                    current_height += direction*fine_step

                    frame = g.frame
                    if frame is None:
                        score = 0
                        self.log(f"[{label} FINE] iter {fine_iterations}: frame is None")
                    else:
                        # score = calculate_focus_similarity(frame, ref_image)
                        score = sobel_variance_focus_measure(frame)
                        self.focus_score_signal.emit(len(scores), score)


                    delta = score - current_score
                    self.log(f"[{label} FINE] iter {fine_iterations}: score = {score}, delta = {delta}")

                    scores.append((score, f"fine_{fine_iterations}"))

                    if delta > min_score_delta:
                        current_score = score
                        # Keep direction
                    else:
                        # Reverse direction and shrink step
                        direction = not direction
                        fine_step *= 0.9  # Shrink step size
                        self.log(f"[{label} FINE] Reversing direction. New step size = {fine_step:.3f}")

                        # If improvement is very small, stop
                        if abs(delta) < min_score_delta:
                            improvement = False

                    fine_iterations += 1

                # Calculate total distance moved from zero
                final_focus_height = current_height

                self.log(f"[{label}] Focus complete. Height: {final_focus_height:.2f}, Best Score: {current_score:.2f}")
                return final_focus_height, scores
            
            self.log("=== Focusing Sample Stage ===")

            zsp0, ssp = iterative_focus(
                focus_serial=focus_serial,
                coarse_step=coarse_step,
                coarse_points=points_per_pass_coarse,
                fine_initial_step=fine_step,
                label="SAMPLE",
                ref_image=g.reference_image,
                min_score_delta=1,
                max_fine_iterations=50
            )


            # # ------------------- STAMP INSTALLATION -------------------
            # self.log("Waiting for user to install stamp...")
            # self.request_stamp_install.emit()

            # # Wait for response
            # while self.user_stamp_response is None:
            #     time.sleep(0.1)

            # if not self.user_stamp_response:
            #     self.log("User cancelled stamp installation. Aborting focusing thread.")
            #     stop_device(focus_serial, "inertial", 1)
            #     return

            # self.log("User confirmed stamp installation. Proceeding to focus stamp...")


            # # ------------------- FOCUS STAMP -------------------
            # self.log("=== Focusing Stamp Stage ===")

            # dz = 50000

            # move_CCdevice(focus_serial, "servo", None, True, dz, 1000)

            # zst0, sst = iterative_focus(
            #     focus_serial=focus_serial,
            #     coarse_step=coarse_step,
            #     coarse_points=points_per_pass_coarse,
            #     fine_initial_step=fine_step,
            #     label="STAMP",
            #     ref_image=g.reference_image,
            #     min_score_delta=1,
            #     max_fine_iterations=50
            # )

            # move_CCdevice(focus_serial, "servo", None, False, dz + zsp0, 1000)

            # self.log("✅ Focus routine complete — ready to push.")

            # g.stamp_sample_delta_z = zst0 - zsp0
            # self.log(f"Calculated Δz (stamp-sample): {g.stamp_sample_delta_z:.2f}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"[ERROR] Focusing thread crashed:\n{str(e)}")

class PushingThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self):

        super().__init__()

    def run(self):
        self.log = lambda msg: self.log_signal.emit(msg)
        if g.transfer_flag and g.stamp_sample_delta_z is not None:
            dz_to_push = int(0.9 * g.stamp_sample_delta_z)

            g.parameters["Stamp Stage Z-Axis"]["KIMstep"] = abs(dz_to_push)
            g.parameters["Stamp Stage Z-Axis"]["KIMrate"] = 100
            g.parameters["Stamp Stage Z-Axis"]["KIMacceleration"] = 10000
            g.parameters["Stamp Stage Z-Axis"]["KIMvoltage"] = 1000

            self.print_debug(dz_to_push)

            result = move_KIMdevice(
                c_char_p(b"97100512"),
                "inertial",
                1,
                dz_to_push > 0,  # True if moving down
                g.parameters["Stamp Stage Z-Axis"]["KIMstep"],
                g.parameters["Stamp Stage Z-Axis"]["KIMrate"],
                g.parameters["Stamp Stage Z-Axis"]["KIMacceleration"],
                1
            )
            self.log(result)
        else:
            self.log("❌ Transfer flag not set or Δz is undefined.")

    def print_debug(self, dz):
        self.log(f"=== PushingThread ===")
        self.log(f"Δz (stamp - sample): {g.stamp_sample_delta_z:.2f}")
        self.log(f"Moving stamp down by 90% of Δz: {dz} steps")
        self.log(f"Using parameters:")
        for k, v in g.parameters["Stamp Stage Z-Axis"].items():
            self.log(f"  {k}: {v}")


class FocusScorePlot(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

        self.steps = []
        self.scores = []

        self.line_score, = self.ax.plot([], [], marker='o', label="Focus Score")

        self.ax.set_xlabel("Step Index")
        self.ax.set_ylabel("Focus Score")
        self.ax.set_title("Autofocus Progress")
        self.ax.legend(loc="upper right")
        self.ax.grid(True)

        self.draw()

    def update_score(self, step_index, score):
        self.steps.append(step_index)
        self.scores.append(score)

        self.line_score.set_data(self.steps, self.scores)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()

    def reset(self):
        self.steps.clear()
        self.scores.clear()
        self.line_score.set_data([], [])
        self.draw()



class HeatingThread(QThread):
    temp_signal = pyqtSignal(float)

    def __init__(self, port="COM3", baudrate=9600, setpoint=0.0,
                 gains=(0.3, 0.45, 0.001), interval=0.1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.setpoint = setpoint
        self.kp, self.ki, self.kd = gains
        self.interval = interval
        self.running = True
        self.integral = 0.0
        self.prev_error = 0.0

    def _asrl_name(self, port):
        p = port.upper()
        if p.startswith("COM"):
            return f"ASRL{p[3:]}::INSTR"
        return port

    def _safe_query(self, inst, cmd):
        """
        Tries query() first. If termination is empty or device is weird,
        falls back to reading raw bytes.
        """
        inst.write(cmd)
        # small wait can help slow controllers
        self.msleep(50)

        if inst.read_termination:
            return inst.read()
        else:
            raw = inst.read_bytes(128, break_on_termchar=False)
            return raw.decode(errors="replace")

    def run(self):
        inst = None
        try:
            print("[HeatingThread] started")
            rm = pyvisa.ResourceManager()

            resource = self._asrl_name(self.port)
            print(f"[Heater] Opening: {resource}")
            inst = rm.open_resource(resource)

            # --- Serial parameters: adjust to your heater's manual ---
            inst.baud_rate = self.baudrate
            inst.data_bits = 8
            inst.parity = constants.Parity.none
            inst.stop_bits = constants.StopBits.one
            inst.flow_control = constants.VI_ASRL_FLOW_NONE

            inst.timeout = 2000  # keep reads responsive

            # Try the most common terminator first; change if needed!
            inst.write_termination = "\r\n"
            inst.read_termination = "\r\n"

            # Quick connectivity check (TEMP? might be wrong command!)
            try:
                resp = self._safe_query(inst, "TEMP?")
                print("[Heater] TEMP? ->", repr(resp))
            except Exception as e:
                print("[Heater] Initial TEMP? failed:", e)
                # Try alternate terminators quickly
                for term in ["\n", "\r", ""]:
                    try:
                        inst.write_termination = term
                        inst.read_termination = term
                        resp = self._safe_query(inst, "TEMP?")
                        print(f"[Heater] Worked with term={repr(term)}:", repr(resp))
                        break
                    except Exception:
                        pass
                else:
                    raise RuntimeError(
                        "No response from heater. Likely wrong port/serial settings or wrong command set."
                    )

            while self.running:
                try:
                    temp_str = self._safe_query(inst, "TEMP?")
                    temp = float(temp_str.strip())
                    self.temp_signal.emit(temp)
                except Exception as e:
                    print(f"[Heater] Temperature read failed: {e}")
                    self.msleep(int(self.interval * 1000))
                    continue

                error = self.setpoint - temp
                self.integral += error * self.interval
                derivative = (error - self.prev_error) / self.interval

                output = self.kp * error + self.ki * self.integral + self.kd * derivative
                output = max(0.0, min(output, 1.0))

                try:
                    inst.write(f"ISET1:{output:.3f}")
                except Exception as e:
                    print(f"[Heater] Write failed: {e}")

                self.prev_error = error
                self.msleep(int(self.interval * 1000))

        except Exception as e:
            print(f"[Heater] Initialization error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                if inst is not None:
                    inst.close()
            except Exception:
                pass

    def stop(self):
        self.running = False

# Class AnalyzingThread(QThread):
# Launch the image analyzer to extract the wavefront information: return a geometry list in real time


class Transfer(QThread): # This version is only suitable for trabsferring the very first layer
    def __init__(self):
        super().__init__()
        self.subThread1 = FocusingThread()
        # self.subThread2 = PushingThread()
        # self.subThread3 = HeatingThread()
        # self.subThread4 = AnalyzingThread()
    
    def run(self):

        try:
            # Launch autofocus: retrieve sample and stamp z values and images
            if self.subThread1 is not None:
                self.subThread1.start()
                self.subThread1.wait()

            # Approach stamp to sample: use human to determine

            # 5X-10X-20X synchronize: automatically adjust the sample and stamp simulatneously

            # Launch heater

            # if self.subThread2 is not None:
                # self.subThread2.start()

            # After reached the target temperature, continue approaching untill wavefront appears

            # Launch analyzer in 5X while keeping approaching: retrieve wavefront geometry in real time

            # Crosstalk with the flake geometry got from camera: when closeby, switching to 20X

            # Redraw the 20X flake by hand, keep crosstalking until wavefront is fully covered flake

            # Detatching, also launch analyzer plus to determine whether picked up or not

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Transfer ERROR] {e}")
