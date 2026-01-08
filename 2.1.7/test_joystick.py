from threading import Thread
import pygame
import json
import time

"""--------------------------------------------------------------------Callable Global Variables--------------------------------------------------------------------"""

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
                print(event.button)


            # Use the button-device-command mapping for release
            if event.type == pygame.JOYBUTTONUP:
                print(event.button)


            # Check each hat
            if event.type == pygame.JOYHATMOTION:
                # Use the hat-device-command mapping
                hat_value = joystick.get_hat(0)
                print(hat_value)
                

            # Check each axis
            # for i in range(joystick.get_numaxes()):
            #     axis = joystick.get_axis(i)
            #     print(axis)

                # For stamp stage

            # Prevent the loop from running too quickly and overwhelming the system
            time.sleep(0.001)

    # Quitting function
    except KeyboardInterrupt:
        # logging.info("Quitting...")
        print("Quitting...")
        pygame.quit()
