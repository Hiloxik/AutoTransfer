""" Joustick script. """
"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Modules

from threading import Thread
import pygame
import time
import globals
from position import *
from connectivity import *
from movement import *

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Joystick

# A. Dictionary

# Global joystick state dictionary
""" The typical form of joystick_state is a 13-element-command-dictionary: 
      {disconnect, connect, stop, moveCC forward, moveCC reverse, drive sample stage, drive sample stage (direction, velocity), 
       drive microscope, drive microscope (direction, velocity), drive stamp stage, drive stamp stage (direction, velocity), moveKIM forward, moveKIM reverse}.
    The initial form is [False] * 13. """
joystick_state = {}

stop_flag = False  # Define stop_flag in the global scope

# Define button-trigger to device-command mapping
""" The typical form of one mapping is {x: [(m, n)]}, where x, y and z are integers.
    It means when button No.x is pressed, trigger the command No.n in joystick_state to device No.m. """
button_trigger_device_command_mapping = {6: [(7, 1)],
                                         7: [(8, 0)],
                                         9: [(7, 2)],
                                         2: [(4, 11)],
                                         1: [(4, 12)],
                                         3: [(5, 11)],
                                         0: [(5, 12)]
                                         }

# Define button-hold to device-command mapping
""" The typical form of one mapping is {x: [(m, n, p)]}, where x, y and z are integers.
    It means when button No.x is pressed, continuously calling the command No.n in joystick_state to device No.m;
    when button No.x is released, trigger the command No.p in joystick_state to device No.m. """
button_hold_device_command_mapping = {5: [(0, 3, 2)],
                                      4: [(0, 4, 2)]
                                      }

# Define hat to device-command mapping
""" The typical form of one mapping is {(x, y): [(m, n)]}, where x, y are in {-1, 0, 1} and m, n are integers.
    It means when hat No.0 is pressed as (x, y), trigger the command No.n in joystick_state to device No.m. """
hat_device_command_mapping = {(1, 0): [(1, 3)],
                              (-1, 0): [(1, 4)],
                              (0, 1): [(2, 3)],
                              (0, -1): [(2, 4)],
                              (1, 1): [(1, 3), (2, 3)],
                              (1, -1): [(1, 3), (2, 4)],
                              (-1, 1): [(1, 4), (2, 3)],
                              (-1, -1): [(1, 4), (2, 4)]
                              }

# Define axis to device-command mapping
""" The typical form of one mapping is {x: [(m, n)]}, where x, y and z are integers.
    It means when the value of axis No.x is read, trigger the command No.n in joystick_state to device No.m. """
axis_device_command_mapping = {0: [(1, 5)],
                               1: [(2, 5)],
                               3: [(3, 7)]
                               }


"""------------------------------------------------------------------------------------"""
# B. Functions

# These two functions process the real-time value of an axis on the joystick to a continuous motion command
def map_axis_to_step(axis, axis_value):
    # Stamp stage
    if axis == 4 or 5:
        DEAD_ZONE = 0.1
        max_step = 10
    # Sample stage
    else:
        DEAD_ZONE = 0.1
        max_step = 1000

    if abs(axis_value) < DEAD_ZONE:
        return 0

    min_step = 0
    step = min_step + (abs(axis_value)) * (max_step - min_step)
    return step

def process_axis(device_name, i, axis, joystick_state, axis_device_command_mapping, command_position):
    direction = 'left' if axis < 0 else 'right'
    step = map_axis_to_step(i, axis)
    if step != 0 and i in axis_device_command_mapping:  # For non-zero velocity motion
        for device_index, command_index in axis_device_command_mapping[i]:
            if device_index < len(device_name):
                device = device_name[device_index]
                joystick_state[device][command_index] = True
                joystick_state[device][command_position] = [direction, step]

"""------------------------------------------------------------------------------------"""
# C. Controller and main thread

# Class to initiate and start the joystick thread
class Controller:
    def __init__(self, devices, joystick):
        self.devices = devices
        self.joystick = joystick

    def start(self):
        # Start separate threads for the joystick
        joystick_thread = Thread(target=self.joystick.run)
        joystick_thread.start()

# Joystick class
class Joystick:
    def __init__(self, devices, device_name):
        self.devices = devices
        self.device_name = device_name
        self.device_CCdriver = DeviceCCDriver()
        self.last_moved_device = None  # This will store the last moved device
        self.last_disconnected_device = None  # This will store the last disconnected device

        # Initiate the null joystick_state for each device
        for device in device_name:
            joystick_state[device] = [False] * 13

    # Running function

    def run(self):
        joystick_loop_thread = Thread(target=self.joystick_loop)
        poll_joystick_state_thread = Thread(target=self.poll_joystick_state)

        joystick_loop_thread.start()
        poll_joystick_state_thread.start()

    # Joystick thread function
    """ In this function, the thread for joystick is being constructed.
        It continuously check the joystick events through pygame and manage these events into commands for hardware motions. """

    def joystick_loop(self):
        pygame.init()
        # logging.info('joystick connected successfully')
        print('joystick connected successfully')

        # Initialize the joystick
        if pygame.joystick.get_count() > 0:
            # Continue initialization as in your version
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

            # Receive the hardware information on this joystick
            buttons = [f"Button {i}" for i in range(joystick.get_numbuttons())]
            hats = [f"Hat {i}" for i in range(joystick.get_numhats())]
            balls = [f"Ball {i}" for i in range(joystick.get_numballs())]
            axes = [f"Axis {i}" for i in range(joystick.get_numaxes())]

            print("Connected buttons:", buttons)
            print("Connected hats:", hats)
            print("Connected balls:", balls)
            print("Connected axes:", axes)

            # Main loop to get real-time joystick activity
            try:
                while True:
                    event = pygame.event.poll()

                    # Check each button
                    if event.type == pygame.JOYBUTTONDOWN:
                        # Use the button-device-command mapping for trigger
                        if event.button in button_trigger_device_command_mapping:
                            for device_index, command_index in button_trigger_device_command_mapping[event.button]:
                                if device_index < len(self.device_name):
                                    device = self.device_name[device_index]
                                    joystick_state[device][command_index] = True

                        # Use the button-device-command mapping for hold
                        if event.button in button_hold_device_command_mapping:
                            for device_index, hold_command_index, release_command_index in \
                                    button_hold_device_command_mapping[event.button]:
                                # Execute the command continuously while the button is being pressed
                                while joystick.get_button(event.button):
                                    if device_index < len(self.device_name):
                                        device = self.device_name[device_index]
                                        joystick_state[device][hold_command_index] = True
                                    # Call your command function here
                                    pygame.event.pump()  # Update event stack

                    # Use the button-device-command mapping for release
                    if event.type == pygame.JOYBUTTONUP:
                        if event.button in button_hold_device_command_mapping:
                            for device_index, hold_command_index, release_command_index in \
                                    button_hold_device_command_mapping[event.button]:
                                if device_index < len(self.device_name):
                                    device = self.device_name[device_index]
                                    joystick_state[device][hold_command_index] = False
                                    joystick_state[device][release_command_index] = False

                    # Check each hat
                    if event.type == pygame.JOYHATMOTION:
                        # Use the hat-device-command mapping
                        hat_value = joystick.get_hat(0)
                        if hat_value in hat_device_command_mapping:
                            for device_index, command_index in hat_device_command_mapping[hat_value]:
                                if device_index < len(self.device_name):
                                    device = self.device_name[device_index]

                                    joystick_state[device][command_index] = True

                    # Check each axis
                    for i in range(joystick.get_numaxes()):
                        axis = joystick.get_axis(i)

                        # For stamp stage
                        if i in {2, 3}:
                            process_axis(self.device_name, i, axis, joystick_state, axis_device_command_mapping, 8)

                        # For other cases
                        else:
                            if i == 1:
                                axis = -axis  # Reverse axis-1
                            process_axis(self.device_name, i, axis, joystick_state, axis_device_command_mapping, 6)

                    # Prevent the loop from running too quickly and overwhelming the system
                    time.sleep(0.001)

            # Quitting function
            except KeyboardInterrupt:
                # logging.info("Quitting...")
                print("Quitting...")
                pygame.quit()

    def stop(self):  # Add a stop method to set the flag
        self.gui_alive = False

    # Main function to convert joystick_state commands into real hardware motion
    """ This function continuoustly check the joystick_state for each device. 
        Once one state is read as 'True', the corresponding command is triggered. """

    def poll_joystick_state(self):

        while True:
            for device_name in self.device_name:  # Iterate over each device
                # print(joystick_state[device_name])
                if joystick_state[device_name][0]:
                    self.connect_device(self.last_disconnected_device)  # Connect last disconnected device
                if joystick_state[device_name][1]:
                    self.disconnect_device(self.last_moved_device)  # Disconnect last moved device
                if joystick_state[device_name][2]:
                    self.stop_device(self.last_moved_device)  # Stop last moved device
                if joystick_state[device_name][3]:
                    self.move_CCdevice(device_name, True)  # Move forward sample stage
                if joystick_state[device_name][4]:
                    self.move_CCdevice(device_name, False)  # Move reverse sample stage
                if joystick_state[device_name][5]:
                    direction, velocity = joystick_state[device_name][
                        6]  # Store (direction, velocity) for sample stage motion
                    globals.parameters[device_name]["CCvelocity"] += velocity
                    if direction == 'right':
                        self.move_CCdevice(device_name, True)  # Continuous move forward sample stage
                    if direction == 'left':
                        self.move_CCdevice(device_name, False)  # Continuous move reverse sample stage
                    # parameters[device_name]["CCstep"] -= step
                if joystick_state[device_name][7]:
                    direction, velocity = joystick_state[device_name][
                        8]  # Store (direction, velocity) for microscope motion
                    globals.parameters[device_name]["CCstep"] += velocity
                    if direction == 'right':
                        self.move_CCdevice(device_name, True)  # Continuous move forward microscope
                    if direction == 'left':
                        self.move_CCdevice(device_name, False)  # Continuous move reverse microscope
                    # parameters[device_name]["CCstep"] -= step
                if joystick_state[device_name][9]:
                    direction, velocity = joystick_state[device_name][
                        10]  # Store (direction, velocity) for stamp stage motion
                    globals.parameters[device_name]["KIMrate"] += velocity
                    if direction == 'right':
                        self.move_KIMdevice(device_name, True)  # Continuous move forward stamp stage
                    if direction == 'left':
                        self.move_KIMdevice(device_name, False)  # Continuous move reverse stamp stage
                    globals.parameters[device_name]["KIMrate"] -= velocity
                if joystick_state[device_name][11]:
                    self.move_KIMdevice(device_name, True)  # Move forward stamp stage
                if joystick_state[device_name][12]:
                    self.move_KIMdevice(device_name, False)  # Move reverse stamp stage

                # Reset joystick_state after checking
                joystick_state[device_name] = [False] * 13
            # Sleep for 0.01 ms
            time.sleep(0.01)

    # Function to obtain the device information
    """ Information including device_serial_num, device_type and device_channel.
        Special_device_name makes sure the two special cases: last_disconnected device and last_moved device. """

    def get_device_info(self, device_name, special_device_name):
        """Access the basic information of devices."""
        specific_device_name = special_device_name if device_name == special_device_name else device_name
        device_serial_num = next(
            (device.device_serial_num for device in self.devices if device.device_name == specific_device_name), None)
        device_type = next(
            (device.device_type for device in self.devices if device.device_name == specific_device_name), None)
        device_channel = next(
            (device.device_channel for device in self.devices if device.device_name == specific_device_name), None)
        return device_serial_num, device_type, device_channel

    # Implement connect, disconnect, stop, move, drive, etc. commands to devices
    def connect_device(self, device_name):
        """Connect devices."""
        device_serial_num, device_type, device_channel = self.get_device_info(device_name,
                                                                              self.last_disconnected_device)
        if device_serial_num is not None:
            status_message = connect_device(device_serial_num, device_type, device_channel)
            print(status_message)
        else:
            print(f"No device found with name {device_name}")

    def disconnect_device(self, device_name):
        """Disconnect devices."""
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, self.last_moved_device)
        if device_serial_num is not None:
            status_message = disconnect_device(device_serial_num, device_type, device_channel)
            print(status_message)
            self.last_disconnected_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def stop_device(self, device_name):
        """Stop devices."""
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, self.last_moved_device)
        if device_serial_num is not None:
            if device_channel is None:
                self.device_CCdriver.stop_drive()
            else:
                stop_device(device_serial_num, device_type, device_channel)
            status_message = stop_device(device_serial_num, device_type, device_channel)
            print(status_message)
        else:
            print(f"No device found with name {device_name}")

    def move_CCdevice(self, device_name, direction):
        """Move DC motors."""
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        if device_serial_num is not None:
            if device_name == 'Sample Stage Rotator':
                velocity = globals.parameters[device_name]["CCvelocity"] * 10
                step = globals.parameters[device_name]["CCstep"] * 10
            else:
                velocity = globals.parameters[device_name]["CCvelocity"]
                step = globals.parameters[device_name]["CCstep"]  # Use a default step for joystick control
            status_message = move_CCdevice(device_serial_num, device_type, device_channel, direction, step, velocity)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def drive_CCdevice(self, device_name, direction):
        """Drive DC motors."""
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        if device_serial_num is not None:
            if device_name == 'Sample Stage Rotator':
                velocity = globals.parameters[device_name]["CCvelocity"] * 10
                step = globals.parameters[device_name]["CCstep"] * 10
            else:
                velocity = globals.parameters[device_name]["CCvelocity"]
                step = globals.parameters[device_name]["CCstep"]  # Use a default step for joystick control

        if device_serial_num is not None:
            status_message = self.device_driver.drive_device(device_serial_num, device_type, device_channel, direction,
                                                             step, velocity)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def move_KIMdevice(self, device_name, direction):
        """Move piezos."""
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        step = globals.parameters[device_name]["KIMstep"]
        rate = globals.parameters[device_name]["KIMrate"]
        acceleration = globals.parameters[device_name]["KIMacceleration"]
        mode = globals.parameters[device_name]["KIMjogmode"]

        status_message = move_KIMdevice(device_serial_num, device_type, device_channel, direction, step,
                                        rate, acceleration, mode)
        print(status_message)
        self.last_moved_device = device_name

    def drive_KIMdevice(self, device_name, direction):
        """Drive piezos."""
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        voltage = globals.parameters[device_name]["KIMvoltage"]
        rate = globals.parameters[device_name]["KIMrate"]
        acceleration = globals.parameters[device_name]["KIMacceleration"]

        if device_serial_num is not None:
            status_message = drive_KIMdevice(device_serial_num, device_type, device_channel, direction,
                                             voltage, rate, acceleration)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")
