"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Global variables

"""------------------------------------------------------------------------------------"""
# A. Device variables

# Initial global parameters for all devices
parameters = {
    "Microscope": {
        "CCstep": 5000,
        "CCvelocity": 1000,
    },
    "Sample Stage X-Axis": {
        "CCstep": 5000,
        "CCvelocity": 1000,
        "small_step_size": 500,
    },
    "Sample Stage Y-Axis": {
        "CCstep": 5000,
        "CCvelocity": 1000,
        "small_step_size": 500,
    },
    "Sample Stage Rotator": {
        "CCstep": 10000,
        "CCvelocity": 1000,
        "small_angle_size": 1000
    },
    "Stamp Stage X-Axis": {
        "KIMstep": 1000,
        "KIMrate": 1000,
        "KIMacceleration": 10000,
        "KIMjogmode": 2,
        "KIMvoltage": 1000,
    },
    "Stamp Stage Y-Axis": {
        "KIMstep": 1000,
        "KIMrate": 1000,
        "KIMacceleration": 10000,
        "KIMjogmode": 2,
        "KIMvoltage": 1000,
    },
    "Stamp Stage Z-Axis": {
        "KIMstep": 1000,
        "KIMrate": 1000,
        "KIMacceleration": 10000,
        "KIMjogmode": 2,
        "KIMvoltage": 1000,
    },
    "Camera": {
        "Rescale": (25580, 19060),
        "Scalebar": 100,
    }
}

"""------------------------------------------------------------------------------------"""
# B. Camera frame variables

# Camera
original_frame_width, original_frame_height = None, None
disaligning = True
Frame = None
mode = "default"
radius = 0
center = None
origin_coordinate = None
uniformity = 0
transfer_flag = False
camera_thread = None


r_offset = 0
g_offset = 0
b_offset = 0
brightness = 0
contrast = 1.0
blur_ksize = 1  # Must be odd number, min 1
gamma = 150
x_scale, y_scale = 1, 1
zoom_factor = 1.0
top, left = 0, 0
blur_ksize = 1
frame = None

# For manual correction
manual_x_shift = 0  # tweak this number
manual_y_shift = 0   # tweak this number

reference_image = None
image_analysis_group = None
image_analysis_log = None

gui_instance = None

stamp_sample_delta_z = None