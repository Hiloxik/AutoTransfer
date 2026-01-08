"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Modules

from ctypes import *
from connectivity import *
import time
import threading

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Movement functions
# A. General commands

stop_flag = False  # Define stop_flag in the global scope

# Home a device
def home_device(device_serial_num, device_type, device_channel):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."
        call_lib(device_type, "Home", device_serial_num, c_int(int(device_channel)))
        time.sleep(0.1)
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} homed successfully."
    else:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        call_lib(device_type, "Home", device_serial_num)
        time.sleep(0.1)
        return f"Device {device_serial_num.value.decode()} homed successfully."

# Stop a device
def stop_device(device_serial_num, device_type, device_channel):
    if device_channel is not None:
        connecton_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connecton_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."
        call_lib(device_type, "MoveStop", device_serial_num, c_int(int(device_channel)))
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} stopped successfully."
    else:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        call_lib(device_type, "StopImmediate", device_serial_num)
        return f"Device {device_serial_num.value.decode()} stopped successfully."


"""------------------------------------------------------------------------------------"""
# B. KDC commands

# Move a KDC device
def move_CCdevice(device_serial_num, device_type, device_channel, direction, step, velocity):
    if device_channel is None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."

        new_vel_param = c_int(int(velocity))
        call_lib(device_type, "SetVelParams", device_serial_num, new_vel_param)

        call_lib(device_type, "RequestPosition", device_serial_num)

        dev_pos = c_int(call_lib(device_type, "GetPosition", device_serial_num))

        new_pos_real = c_int(int(step))  # in real units
        call_lib(device_type, "SetJogStepSize", device_serial_num, new_pos_real)

        call_lib(device_type, "SetJogMode", device_serial_num, c_int(int(2)), c_int(int(1)))
        # print(dev_pos)

        if direction:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(2)))
        else:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(1)))
        # return f"Device {device_serial_num.value.decode()} moved successfully."
        return

# Drive a KDC device
class DeviceCCDriver:
    def __init__(self):
        self.stop_event = threading.Event()
        self.drive_thread = None

    def drive_device(self, device_serial_num, device_type, device_channel, direction, step, velocity):
        # Check connection
        connected, msg = is_connected(device_serial_num, device_type, device_channel)
        if not connected:
            return f"[ERROR] Device {device_serial_num.value.decode()} not connected: {msg}"

        # Set velocity (verify API function name for your device type)
        call_lib(device_type, "SetVelParams", device_serial_num, c_int(0), c_int(int(velocity)))

        self.stop_event.clear()

        # Determine motion command
        move_right = direction.lower() == 'right'
        move_left = direction.lower() == 'left'

        # Start motion
        while not self.stop_event.is_set():
            if move_right:
                call_lib(device_type, "MoveRelative", device_serial_num, c_int(int(step)))
            elif move_left:
                call_lib(device_type, "MoveRelative", device_serial_num, c_int(-int(step)))
            else:
                break  # stop direction or invalid command

            # Wait until move completes (polling-based)
            while True:
                if self.stop_event.is_set():
                    call_lib(device_type, "StopImmediate", device_serial_num)
                    break

                status = call_lib(device_type, "GetStatusBits", device_serial_num)
                # Bit 0x00000010 = "in motion" (per Kinesis API)
                if (status & 0x00000010) == 0:
                    break

                time.sleep(0.05)

            # Small pause between moves
            time.sleep(0.05)

        # Stop safely
        call_lib(device_type, "StopImmediate", device_serial_num)
        call_lib(device_type, "SetVelParams", device_serial_num, c_int(0), c_int(0))
        return f"[INFO] Device {device_serial_num.value.decode()} stopped safely."

    def start_drive(self, device_serial_num, device_type, device_channel, direction, step, velocity):
        if self.drive_thread and self.drive_thread.is_alive():
            return "[ERROR] Drive thread already running."

        self.stop_event.clear()
        self.drive_thread = threading.Thread(
            target=self.drive_device,
            args=(device_serial_num, device_type, device_channel, direction, step, velocity),
            daemon=True
        )
        self.drive_thread.start()

        return f"[INFO] Started driving device {device_serial_num.value.decode()} {direction}."

    def stop_drive(self, device_serial_num=None, device_type=None):
        if not self.stop_event.is_set():
            self.stop_event.set()
            if device_serial_num and device_type:
                try:
                    call_lib(device_type, "StopImmediate", device_serial_num)
                except Exception:
                    pass
            return "[INFO] Stop command sent."
        return "[WARN] Stop already requested."

# Set move step for a KDC device
def set_CCstep(device_serial_num, device_type, device_channel, step):
    if device_channel is None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        step = c_int(int(step))
        call_lib(device_type, "SetJogStepSize", device_serial_num, step)
        return f"Step parameter set successfully for device {device_serial_num.value.decode()}."

# Set move velocity for a KDC device
def set_CCvelocity(device_serial_num, device_type, device_channel, new_vel_param):
    if device_channel is None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        new_vel_param = c_int(int(new_vel_param))
        call_lib(device_type, "SetVelParams", device_serial_num, new_vel_param)
        return f"Velocity parameters set successfully for device {device_serial_num.value.decode()}."

"""------------------------------------------------------------------------------------"""
# C. KIM commands

# Move a KIM device
def move_KIMdevice(device_serial_num, device_type, device_channel, direction, step, rate, acceleration, mode):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."

        call_lib(device_type, "RequestCurrentPosition", device_serial_num, device_type)
        dev_pos = c_int(call_lib(device_type, "GetCurrentPosition", device_serial_num, device_type))

        new_pos_param = c_int(int(step))
        new_rat_param = c_int(int(rate))
        new_acc_param = c_int(int(acceleration))
        new_mod_param = c_int(int(mode))

        print(new_pos_param, new_rat_param, new_acc_param)

        call_lib(device_type, "SetJogParameters", device_serial_num, c_int(int(device_channel)), new_mod_param,
                 new_pos_param, new_pos_param, new_rat_param, new_acc_param)

        print(dev_pos)

        if direction:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(2)))
        else:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(1)))
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} moved successfully."

# Drive a KIM device
def drive_KIMdevice(device_serial_num, device_type, device_channel, direction, maxvoltage, rate, acceleration):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."

        call_lib(device_type, "RequestCurrentPosition", device_serial_num, device_type)
        dev_pos = c_int(call_lib(device_type, "GetCurrentPosition", device_serial_num, device_type))

        new_vol_param = c_int(int(maxvoltage))
        new_rat_param = c_int(int(rate))
        new_acc_param = c_int(int(acceleration))

        call_lib(device_type, "RequestDriveOPParameters", device_serial_num, c_int(int(device_channel)))
        call_lib(device_type, "SetDriveOPParameters", device_serial_num, c_int(int(device_channel)), new_vol_param,
                 new_rat_param, new_acc_param)

        print(dev_pos)

        if direction:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(2)))
        else:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(1)))
    return f"Device {device_serial_num.value.decode()} Channel {device_channel} moved successfully."

# Set jog parameters for a KIM device
def set_KIMjog(device_serial_num, device_type, device_channel, mode, stepfor, steprev, rate, acceleration):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."
        stepfor = c_int(int(stepfor))
        steprev = c_int(int(steprev))
        rate = c_int(int(rate))
        acceleration = c_int(int(acceleration))
        call_lib(device_type, "SetJogParameters", device_serial_num, c_int(int(device_channel)), c_int(int(mode)),
                 stepfor, steprev, rate, acceleration)
        return f"Step parameter set successfully for device {device_serial_num.value.decode()} Channel {device_channel}."