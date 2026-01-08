# ---------------------------------------------------------------------------
# Modules
from ctypes import *
import os
import sys
import time

# ---------------------------------------------------------------------------
# Load Thorlabs Libraries

# DLL path
KINEMATICS_DLL_PATH = r"C:\Program Files\Thorlabs\Kinesis"

# Handle Python version for DLL loading
if sys.version_info < (3, 8):
    os.chdir(KINEMATICS_DLL_PATH)
else:
    os.add_dll_directory(KINEMATICS_DLL_PATH)

# Load necessary libraries
lib_device_mgr = cdll.LoadLibrary("Thorlabs.MotionControl.DeviceManager.dll")
lib_servo = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.DCServo.dll")
lib_inertial = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.InertialMotor.dll")

# ---------------------------------------------------------------------------
# Helper: Command dispatcher

def call_lib(device_type, command, *args):
    lib = lib_servo if device_type == "servo" else lib_inertial
    prefix = "CC_" if device_type == "servo" else "KIM_"
    command_method = getattr(lib, prefix + command, None)
    if command_method is not None:
        return command_method(*args)
    else:
        raise Exception(f"Invalid command '{command}' for device type '{device_type}'.")

# ---------------------------------------------------------------------------
# Device Connection Functions

def connect_device(device_serial_num: c_char_p, device_type: str, device_channel: int = None) -> str:
    # Step 1: Build device list
    if lib_device_mgr.TLI_BuildDeviceList() != 0:
        return "[ERROR] Failed to build device list."

    # Step 2: Initialize simulation environment
    # if device_type == "servo":
    #     if lib_servo.TLI_InitializeSimulations() != 0:
    #         return "[ERROR] Failed to initialize servo simulations."
    # else:
    #     if lib_inertial.TLI_InitializeSimulations() != 0:
    #         return "[ERROR] Failed to initialize inertial simulations."

    # Step 3: Open the device
    open_result = call_lib(device_type, "Open", device_serial_num)
    if open_result != 0:
        return f"[ERROR] Failed to open device {device_serial_num.value.decode()}. Code: {open_result}"

    # Optional: Enable channel for inertial devices
    if device_type == "inertial" and device_channel is not None:
        enable_result = call_lib(device_type, "EnableChannel", device_serial_num, c_int(device_channel))
        if enable_result != 0:
            return f"[ERROR] Failed to enable channel {device_channel} for device {device_serial_num.value.decode()}. Code: {enable_result}"

    # Step 4: Wait for device to initialize
    time.sleep(0.3)

    # Step 5: Start polling
    poll_result = call_lib(device_type, "StartPolling", device_serial_num, c_int(200))
    # if poll_result != 0:
    #     return f"[ERROR] Failed to start polling device {device_serial_num.value.decode()}. Code: {poll_result}"

    # Success
    if device_type == "inertial" and device_channel is not None:
        print(f"Device {device_serial_num.value.decode()} Channel {device_channel} connected successfully.")
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} connected successfully."
    else:
        print(f"Device {device_serial_num.value.decode()} connected successfully.")
        return f"Device {device_serial_num.value.decode()} connected successfully."

def disconnect_device(device_serial_num: c_char_p, device_type: str, device_channel: int = None) -> str:
    # Stop polling and close device
    if device_type == 'inertial':
        if device_channel is not None:
            call_lib(device_type, "DisableChannel", device_serial_num, c_int(device_channel))
        call_lib(device_type, "StopPolling", device_serial_num)
        call_lib(device_type, "Close", device_serial_num)
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} disconnected successfully."
    else:
        call_lib(device_type, "StopPolling", device_serial_num)
        call_lib(device_type, "Close", device_serial_num)
        return f"Device {device_serial_num.value.decode()} disconnected successfully."

def is_connected(device_serial_num: c_char_p, device_type: str, device_channel: int = None):
    try:
        open_ok = call_lib(device_type, "Open", device_serial_num) == 0
        if device_type == "inertial" and device_channel is not None:
            enable_ok = call_lib(device_type, "EnableChannel", device_serial_num, c_int(device_channel)) == 0
            return open_ok and enable_ok, "" if open_ok and enable_ok else "Device not connected properly."
        return open_ok, "" if open_ok else "Device not connected."
    except Exception as e:
        return False, f"[ERROR] Exception during connection check: {e}"
