""" Camera script. Including camera connection, different modes, and image processing/tracking. """
"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Modules

import cv2
import numpy as np
import os
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog
from pypylon import pylon
import globals as g  # rename for clarity

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QFileDialog, QSizePolicy, QSlider
from PyQt5.QtGui import QImage, QPixmap, QMouseEvent, QWheelEvent
from PyQt5.QtCore import Qt

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Global variables in different modes

# Frame
frame = None
x_scale, y_scale = 1, 1
zoom_factor = 1.0
top, left = 0, 0
r_offset, g_offset, b_offset = 0, 0, 0
brightness, contrast = 0, 1
blur_ksize = 1

# Tracking mode
tracking = False # Flag for tracking mode
tracker = None # Flag for auto-tracking
polygon = [] # Polygon (generated) list
poly_shifted = [] # Polygon (shifted) list
closed = False # Flag for polygon closure
highlighted_point = None
attraction_range = int(20 * zoom_factor) 
old_center = None
bbox = None
dragging = False
shift_vector = (0, 0)
polygon_profile = {'center': None, 'points': [], 'edges': [], 'angle': 0}  # New variable
center_shift_vector = (0, 0)  # Initialize the shift vector to (0, 0)
initial_center = None  # Store the initial center when the polygon is closed

# Drawing mode
drawing_polygon = []
drawing_polygons = []
drawing_polygon_profile = {'center': None, 'points': [], 'edges': [], 'angle': 0}  # New variable
drawing_dragging_index = -1
drawing_poly_shifted = []
drawing_closed = False
drawing_erased = False
drawing_highlighted_point = None
drawing_dragging = False
drawing_shift_vector = (0, 0)
colors = [(255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
          (0, 255, 255), (255, 255, 255)]  # Add more colors if needed
color_index = 0

# Measuring mode
ruler_start = None
ruler_end = None

# Default mode
dragging_frame = False
drag_start_x = 0
drag_start_y = 0

# Transfer mode
last_uniformity = None
THRESHOLD = 5

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Global functions

def get_polygon():
    global drawing_polygon_profile
    return drawing_polygon_profile

def get_polygon_tracker():
    global polygon_profile
    return polygon_profile


def get_shift():
    global center_shift_vector
    # center_shift_vector = shift_vector
    return center_shift_vector


def get_angle():
    return drawing_polygon_profile['angle']


def zoom_in_camera():
    global zoom_factor
    MAX_ZOOM = 5
    zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)


def zoom_out_camera():
    global zoom_factor
    MIN_ZOOM = 0.5
    zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)


def calculate_color_uniformity(frame):
    # Convert the frame to grayscale if it is in color
    if len(frame.shape) == 3:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray_frame = frame

    # Compute the standard deviation of the grayscale values
    return np.std(gray_frame)

def draw_frame(frame):
    # Draw a sleek frame around the camera view
    thickness = 10  # Adjust the thickness to your preference
    color = (0, 0, 0)  # A light cyan color, but you can customize
    cv2.line(frame, (0, 0), (frame.shape[1], 0), color, thickness)
    cv2.line(frame, (0, 0), (0, frame.shape[0]), color, thickness)
    cv2.line(frame, (frame.shape[1] - 1, 0), (frame.shape[1] - 1, frame.shape[0]), color, thickness)
    cv2.line(frame, (0, frame.shape[0] - 1), (frame.shape[1], frame.shape[0] - 1), color, thickness)

def is_within_attraction(p1, p2, radius):
    return np.linalg.norm(np.array(p1) - np.array(p2)) < radius

def apply_color_correction(frame):
    # === Gamma correction ===
    gamma = g.gamma / 100.0  # g.gamma from slider
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    corrected = cv2.LUT(frame, table)

    # === Simple white balance (Gray World) ===
    avg_b = np.mean(corrected[..., 0])
    avg_g = np.mean(corrected[..., 1])
    avg_r = np.mean(corrected[..., 2])
    avg = (avg_b + avg_g + avg_r) / 3

    scale_b = avg / (avg_b + 1e-6)
    scale_g = avg / (avg_g + 1e-6)
    scale_r = avg / (avg_r + 1e-6)

    balanced = corrected.copy()
    balanced[..., 0] = np.clip(corrected[..., 0] * scale_b, 0, 255)
    balanced[..., 1] = np.clip(corrected[..., 1] * scale_g, 0, 255)
    balanced[..., 2] = np.clip(corrected[..., 2] * scale_r, 0, 255)

    return balanced.astype("uint8")

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Mouse interaction in different modes

# A. Frame interaction
def mouse_callback(event, x, y, flags, param):
    global x_scale, y_scale, zoom_factor, top, left, frame
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, polygon_profile
    global drawing_polygon, drawing_polygons, drawing_dragging_index, drawing_closed, drawing_highlighted_point, \
        drawing_dragging, drawing_poly_shifted, drawing_shift_vector, initial_center, color_index, drawing_polygon_profile
    global ruler_start, ruler_end

    # 1. Reverse the resize transformation
    x_rescaled = x * frame.shape[1] / 640
    y_rescaled = y * frame.shape[0] / 480

    # 2. Adjust for the zoom
    x_zoomed = int(x_rescaled / zoom_factor)
    y_zoomed = int(y_rescaled / zoom_factor)

    # 3. Account for translation due to zoom
    x_original = x_zoomed + left
    y_original = y_zoomed + top

    # Render point on the original frame
    cv2.circle(frame, (x_original, y_original), 5, (0, 0, 255), -1)
    # Render point on the resized frame exactly where clicked
    cv2.circle(globals.Frame, (x, y), 5, (0, 255, 0), -1)

    # Handle different modes
    if globals.mode == "measuring":
        handle_measuring_mode(event, x_original, y_original, flags, param)
    elif globals.mode == "drawing":
        handle_drawing_mode(event, x_original, y_original, flags, param)
    elif globals.mode == "tracking":
        handle_tracking_mode(event, x_original, y_original, flags, param)
    elif globals.mode == "default":
        handle_default_mode(event, x, y, flags, param)

"""------------------------------------------------------------------------------------"""
# B. Default mode interaction

""" This mode is the default mode, in which user can use mouse to drag the frame if zoomed in. """
def handle_default_mode(event, x, y, flags, param):
    global dragging_frame, drag_start_x, drag_start_y, left, top, frame, zoom_factor

    if event == cv2.EVENT_LBUTTONDOWN:
        dragging_frame = True
        drag_start_x = x
        drag_start_y = y

    elif event == cv2.EVENT_MOUSEMOVE:
        if dragging_frame and zoom_factor > 1.0:
            dx = int((x - drag_start_x) / zoom_factor)
            dy = int((y - drag_start_y) / zoom_factor)
            left -= dx
            top -= dy
            drag_start_x = x
            drag_start_y = y
            # Here, you should also make sure 'left' and 'top' values don't go out of frame bounds.

    elif event == cv2.EVENT_LBUTTONUP:
        dragging_frame = False

"""------------------------------------------------------------------------------------"""
# C. Drawing mode interaction

""" This mode is the drawing mode, in which user can use mouse to draw, drag, rotate, delete different coloful multiple polygons without a tracking algorithm planted in. 
    This mode is used to create targert flake patterns and design device patterns that user aim to assembly and transfer. """
def handle_drawing_mode(event, x, y, flags, param):
    global drawing_polygon, drawing_polygons, drawing_dragging_index, drawing_closed, drawing_highlighted_point, drawing_dragging, drawing_poly_shifted, drawing_shift_vector, \
        color_index, initial_center, drawing_polygon_profile, drawing_erased

    if event == cv2.EVENT_LBUTTONDOWN:
        if drawing_erased:
            drawing_erased = False
            return

        if drawing_closed and drawing_poly_shifted:
            # ✅ Finalize the current closed polygon and prepare to drag
            drawing_dragging = False
            drawing_dragging_index = -1

            if drawing_polygon:  # Only add if the polygon is not empty
                drawing_polygons.append((drawing_polygon, colors[color_index]))  # Add current polygon to list

            # Reset for a new polygon
            drawing_polygon = []
            # drawing_closed = False
            drawing_highlighted_point = None

            # Check if clicked inside any polygon to start dragging
            for draw_idx, (draw_polygon, _) in enumerate(drawing_polygons):
                if draw_polygon:
                    draw_poly_np = np.array(draw_polygon, dtype=np.int32)
                    if cv2.pointPolygonTest(draw_poly_np, (x, y), False) >= 0:
                        drawing_dragging = True
                        drawing_dragging_index = draw_idx
                        drawing_shift_vector = (x, y)
                        break
            else:
                # Clicked outside existing polygons — start new polygon
                drawing_polygon = [(x, y)]
                color_index = (color_index + 1) % len(colors)
                drawing_polygon_profile['angle'] = 0

        elif not drawing_polygon:
            # ✅ First point of a new polygon
            drawing_polygon.append((x, y))
            drawing_closed = False
            drawing_highlighted_point = None
            drawing_polygon_profile['angle'] = 0

        else:
            # ✅ Check if we're near the first point to close the polygon
            first_point = drawing_polygon[0]
            if is_within_attraction((x, y), first_point, attraction_range) and len(drawing_polygon) > 2:
                drawing_polygon.append(first_point)  # Snap to first point
                drawing_closed = True
                drawing_highlighted_point = first_point
                drawing_poly_shifted = drawing_polygon.copy()
                initial_center = (
                    sum(p[0] for p in drawing_poly_shifted) / len(drawing_poly_shifted),
                    sum(p[1] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
                )
                drawing_polygon_profile['angle'] = 0
            else:
                # ✅ Add point only if not overlapping an existing one
                if all(not is_within_attraction((x, y), pt, attraction_range) for pt in drawing_polygon):
                    drawing_polygon.append((x, y))
                    drawing_closed = False
                    drawing_highlighted_point = None
                    drawing_polygon_profile['angle'] = 0


    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing_dragging:
            draw_dx, draw_dy = x - drawing_shift_vector[0], y - drawing_shift_vector[1]
            drawing_shift_vector = (x, y)
            drawing_poly_shifted = [(draw_p[0] + draw_dx, draw_p[1] + draw_dy) for draw_p in drawing_poly_shifted]
            # Update the polygon_profile with the new coordinates and center
            drawing_center_x = sum(p[0] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            drawing_center_y = sum(p[1] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            drawing_polygon_profile['center'] = (drawing_center_x, drawing_center_y)
            drawing_polygon_profile['points'] = drawing_poly_shifted
            drawing_polygon_profile['edges'] = [np.sqrt(
                (drawing_poly_shifted[i][0] - drawing_poly_shifted[i - 1][0]) ** 2 + (
                        drawing_poly_shifted[i][1] - drawing_poly_shifted[i - 1][1]) ** 2)
                for i in range(1, len(drawing_poly_shifted))]
            drawing_polygon_profile['edges'].append(
                np.sqrt((drawing_poly_shifted[0][0] - drawing_poly_shifted[-1][0]) ** 2 + (
                        drawing_poly_shifted[0][1] - drawing_poly_shifted[-1][
                    1]) ** 2))  # Add the edge between the last and first points
            if drawing_dragging_index == len(drawing_polygons):  # Current drawing_polygon
                drawing_polygon = [(draw_p[0] + draw_dx, draw_p[1] + draw_dy) for draw_p in drawing_polygon]
                # Update the polygon_profile with the new coordinates and center

            else:  # Existing polygon in drawing_polygons
                draw_polygon, draw_color = drawing_polygons[drawing_dragging_index]
                drawing_polygons[drawing_dragging_index] = (
                    [(draw_p[0] + draw_dx, draw_p[1] + draw_dy) for draw_p in draw_polygon], draw_color)

        else:
            drawing_highlighted_point = None
            if drawing_polygon and not drawing_closed:
                for point in drawing_polygon:
                    if is_within_attraction((x, y), point, attraction_range):
                        drawing_highlighted_point = point
                        break

    elif event == cv2.EVENT_RBUTTONDOWN:
        if drawing_polygon:
            drawing_erased = True  # <-- set flag
            drawing_polygon = []
            drawing_poly_shifted = []
            drawing_closed = False
            drawing_highlighted_point = None
            drawing_polygon_profile['angle'] = 0
        elif drawing_polygons:
            drawing_polygons.pop()

    elif event == cv2.EVENT_LBUTTONUP:
        drawing_dragging = False
        if drawing_closed:
            drawing_center_x = sum(p[0] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            drawing_center_y = sum(p[1] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            drawing_polygon_profile['center'] = (drawing_center_x, drawing_center_y)
            drawing_polygon_profile['points'] = drawing_poly_shifted
            drawing_polygon_profile['edges'] = [np.sqrt(
                (drawing_poly_shifted[i][0] - drawing_poly_shifted[i - 1][0]) ** 2 + (
                        drawing_poly_shifted[i][1] - drawing_poly_shifted[i - 1][1]) ** 2)
                for i in range(1, len(drawing_poly_shifted))]
            drawing_polygon_profile['edges'].append(
                np.sqrt((drawing_poly_shifted[0][0] - drawing_poly_shifted[-1][0]) ** 2 + (
                        drawing_poly_shifted[0][1] - drawing_poly_shifted[-1][
                    1]) ** 2))  # Add the edge between the last and first points

    elif event == cv2.EVENT_MOUSEWHEEL:
        if drawing_closed:
            # Determine the direction of rotation
            draw_rotation_angle = 1 if flags > 0 else -1
            # Calculate the center of the polygon
            draw_center_x = sum(p[0] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            draw_center_y = sum(p[1] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            draw_center = (draw_center_x, draw_center_y)

            # Define the rotation matrix
            draw_M = cv2.getRotationMatrix2D(draw_center, draw_rotation_angle, 1)

            # Rotate each point of the polygon
            drawing_poly_shifted_rotated = []
            for draw_p in drawing_poly_shifted:
                draw_p_rotated = np.dot(draw_M, (draw_p[0], draw_p[1], 1))
                drawing_poly_shifted_rotated.append((draw_p_rotated[0], draw_p_rotated[1]))

            drawing_poly_shifted = drawing_poly_shifted_rotated

            # ✅ Clear the original polygon to avoid rendering it again
            drawing_polygon = []

            # ✅ Ensure polygon is marked closed and ready to render rotated version
            drawing_closed = True
            drawing_highlighted_point = None

            # ✅ Update the profile with the new polygon
            drawing_polygon_profile['center'] = draw_center
            drawing_polygon_profile['points'] = drawing_poly_shifted
            drawing_polygon_profile['edges'] = [
                np.sqrt(
                    (drawing_poly_shifted[i][0] - drawing_poly_shifted[i - 1][0]) ** 2 +
                    (drawing_poly_shifted[i][1] - drawing_poly_shifted[i - 1][1]) ** 2
                )
                for i in range(1, len(drawing_poly_shifted))
            ]
            drawing_polygon_profile['edges'].append(
                np.sqrt(
                    (drawing_poly_shifted[0][0] - drawing_poly_shifted[-1][0]) ** 2 +
                    (drawing_poly_shifted[0][1] - drawing_poly_shifted[-1][1]) ** 2
                )
            )
            drawing_polygon_profile['angle'] += draw_rotation_angle
"""------------------------------------------------------------------------------------"""
# D. Tracking mode interaction

""" This mode is the tracking mode, in which users can draw, drag, rotate and delete green single polygon with a tracking algorithm planted in. This mode is used to track current flakes. """
def handle_tracking_mode(event, x, y, flags, param):
    global polygon, tracking, tracker, closed, highlighted_point, bbox
    global old_center, poly_shifted, dragging, shift_vector
    global polygon_profile, center_shift_vector

    # ---------------------------------------------------------------------
    # LEFT MOUSE DOWN → draw or drag polygon
    # ---------------------------------------------------------------------
    if event == cv2.EVENT_LBUTTONDOWN:
        if closed and poly_shifted:
            poly_np = np.array(poly_shifted, dtype=np.int32)
            if cv2.pointPolygonTest(poly_np, (x, y), False) >= 0:
                dragging = True
                tracking = False
                shift_vector = (x, y)
            else:
                # Start new polygon
                polygon = []
                poly_shifted = []
                closed = False
                tracking = False
                highlighted_point = None
                polygon_profile['angle'] = 0
        elif not polygon:
            polygon.append((x, y))
        else:
            first_point = polygon[0]
            if len(polygon) >= 3 and is_within_attraction((x, y), first_point, attraction_range):
                polygon.append(first_point)
                closed = True
                poly_shifted = polygon.copy()
                highlighted_point = first_point

                # Safe bounding box creation
                try:
                    x_b, y_b, w, h = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
                    if w <= 0 or h <= 0:
                        print("❌ Invalid bounding box size.")
                        closed = False
                        return

                    cx, cy = x_b + w / 2, y_b + h / 2
                    bbox = tuple(map(int, (
                        cx - w * 0.6,
                        cy - h * 0.6,
                        w * 1.2,
                        h * 1.2
                    )))
                    old_center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
                    polygon_profile['angle'] = 0
                except Exception as e:
                    print("❌ Error computing bounding box:", e)
                    closed = False
            else:
                if (x, y) not in polygon:
                    polygon.append((x, y))
                    closed = False
                    highlighted_point = None
                    polygon_profile['angle'] = 0

    # ---------------------------------------------------------------------
    # LEFT DOUBLE CLICK → copy from drawing mode
    # ---------------------------------------------------------------------
    elif event == cv2.EVENT_LBUTTONDBLCLK:
        if drawing_closed and drawing_poly_shifted:
            poly_shifted = drawing_poly_shifted.copy()
            polygon_profile = drawing_polygon_profile.copy()
            closed = True

            try:
                x_b, y_b, w, h = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
                if w <= 0 or h <= 0:
                    print("❌ Invalid bbox from drawing polygon.")
                    closed = False
                    return

                cx, cy = x_b + w / 2, y_b + h / 2
                bbox = tuple(map(int, (
                    cx - w * 0.6,
                    cy - h * 0.6,
                    w * 1.2,
                    h * 1.2
                )))
                old_center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
                print("✅ Polygon copied from drawing to tracking mode.")
            except Exception as e:
                print("❌ Error during drawing polygon copy:", e)
                closed = False
        else:
            print("❌ No closed polygon to copy.")

    # ---------------------------------------------------------------------
    # MOUSE MOVE (dragging polygon)
    # ---------------------------------------------------------------------
    elif event == cv2.EVENT_MOUSEMOVE:
        if dragging:
            dx, dy = x - shift_vector[0], y - shift_vector[1]
            shift_vector = (x, y)
            poly_shifted = [(p[0] + dx, p[1] + dy) for p in poly_shifted]

            try:
                x_b, y_b, w, h = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
                cx, cy = x_b + w / 2, y_b + h / 2
                bbox = tuple(map(int, (
                    cx - w * 0.6,
                    cy - h * 0.6,
                    w * 1.2,
                    h * 1.2
                )))
                old_center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)

                # Update profile
                cx = sum(p[0] for p in poly_shifted) / len(poly_shifted)
                cy = sum(p[1] for p in poly_shifted) / len(poly_shifted)
                polygon_profile['center'] = (cx, cy)
                polygon_profile['points'] = poly_shifted
                polygon_profile['edges'] = [np.hypot(
                    poly_shifted[i][0] - poly_shifted[i - 1][0],
                    poly_shifted[i][1] - poly_shifted[i - 1][1]
                ) for i in range(1, len(poly_shifted))]
                polygon_profile['edges'].append(np.hypot(
                    poly_shifted[0][0] - poly_shifted[-1][0],
                    poly_shifted[0][1] - poly_shifted[-1][1]
                ))
            except Exception as e:
                print("❌ Error during dragging bbox update:", e)
        else:
            highlighted_point = None
            if polygon and not closed and len(polygon) >= 3:
                if is_within_attraction((x, y), polygon[0], attraction_range):
                    highlighted_point = polygon[0]

    # ---------------------------------------------------------------------
    # RIGHT CLICK → reset
    # ---------------------------------------------------------------------
    elif event == cv2.EVENT_RBUTTONDOWN:
        polygon = []
        poly_shifted = []
        closed = False
        tracking = False
        highlighted_point = None
        polygon_profile['angle'] = 0

    # ---------------------------------------------------------------------
    # LEFT MOUSE UP → Initialize tracker
    # ---------------------------------------------------------------------
    elif event == cv2.EVENT_LBUTTONUP:
        dragging = False

        if not closed or poly_shifted is None or bbox is None:
            return

        # Defensive check: frame must be available
        if frame is None or frame.size == 0:
            print("❌ Cannot start tracker: frame is empty.")
            return

        # Validate bbox
        _, _, w, h = bbox
        if w <= 0 or h <= 0:
            print("❌ Cannot start tracker: invalid bbox size", bbox)
            return

        try:
            tracker = cv2.legacy.TrackerMOSSE_create()
            tracker.init(frame, bbox)
            tracking = True

            # Update profile again
            cx = sum(p[0] for p in poly_shifted) / len(poly_shifted)
            cy = sum(p[1] for p in poly_shifted) / len(poly_shifted)
            polygon_profile['center'] = (cx, cy)
            polygon_profile['points'] = poly_shifted
            polygon_profile['edges'] = [np.hypot(
                poly_shifted[i][0] - poly_shifted[i - 1][0],
                poly_shifted[i][1] - poly_shifted[i - 1][1]
            ) for i in range(1, len(poly_shifted))]
            polygon_profile['edges'].append(np.hypot(
                poly_shifted[0][0] - poly_shifted[-1][0],
                poly_shifted[0][1] - poly_shifted[-1][1]
            ))

            # Calculate shift vector from drawing profile
            draw_center = drawing_polygon_profile.get('center')
            if draw_center:
                shift_vector = (draw_center[0] - cx, draw_center[1] - cy)
                center_shift_vector = shift_vector
                print("✅ Tracker started. Shift vector:", shift_vector)
        except Exception as e:
            print("❌ Failed to initialize tracker:", e)
            tracking = False
            tracker = None

    # ---------------------------------------------------------------------
    # MOUSE WHEEL → Rotate polygon
    # ---------------------------------------------------------------------
    elif event == cv2.EVENT_MOUSEWHEEL and closed:
        rotation_angle = 1 if flags > 0 else -1
        center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
        center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
        M = cv2.getRotationMatrix2D((center_x, center_y), rotation_angle, 1.0)
        poly_shifted = [tuple(np.dot(M, (p[0], p[1], 1))) for p in poly_shifted]

        polygon_profile['center'] = (center_x, center_y)
        polygon_profile['points'] = poly_shifted
        polygon_profile['edges'] = [np.hypot(
            poly_shifted[i][0] - poly_shifted[i - 1][0],
            poly_shifted[i][1] - poly_shifted[i - 1][1]
        ) for i in range(1, len(poly_shifted))]
        polygon_profile['edges'].append(np.hypot(
            poly_shifted[0][0] - poly_shifted[-1][0],
            poly_shifted[0][1] - poly_shifted[-1][1]
        ))
        polygon_profile['angle'] += rotation_angle

"""------------------------------------------------------------------------------------"""
# E. Measuring mode interaction

def draw_ruler(image, start, end):
    if start is None or end is None:
        return

    # Draw the line
    cv2.line(image, start, end, (0, 255, 0), 2)

    # Draw caps "|"
    cap_length = 10
    cv2.line(image, (start[0], start[1] - cap_length), (start[0], start[1] + cap_length), (0, 255, 0), 2)
    cv2.line(image, (end[0], end[1] - cap_length), (end[0], end[1] + cap_length), (0, 255, 0), 2)

    # Calculate distance
    distance = int(np.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2))

    # Define the position for the text based on the direction of the line
    text_pos = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2 + 20)

    # Put text below the line
    cv2.putText(image, f"{distance} pixels", text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)


def handle_measuring_mode(event, x, y, flags, param):
    global ruler_start, ruler_end, frame

    # Scale the mouse coordinates based on your resizing
    x = int(x * frame.shape[1] / 640)
    y = int(y * frame.shape[0] / 480)

    if event == cv2.EVENT_LBUTTONDOWN:
        if ruler_start is None:
            ruler_start = (x, y)
        else:
            ruler_end = (x, y)
            distance = int(np.sqrt((ruler_end[0] - ruler_start[0]) ** 2 + (ruler_end[1] - ruler_start[1]) ** 2))
            # Reset ruler_start to allow drawing a new ruler
            ruler_start = None
            ruler_end = None

    elif event == cv2.EVENT_MOUSEMOVE and ruler_start is not None:
        # Draw temporary ruler on a copy of the frame
        draw_ruler(frame, ruler_start, (x, y))
        zoom_center = (frame.shape[1] / 2, frame.shape[0] / 2)
        M = cv2.getRotationMatrix2D(zoom_center, 0, zoom_factor)
        zoomed_frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
        resized_frame = cv2.resize(zoomed_frame, (640, 480))
        draw_scale_bar(resized_frame, zoom_factor)
        cv2.imshow("Camera", resized_frame)

    elif event == cv2.EVENT_RBUTTONDOWN:
        # Delete the ruler by resetting the frame
        ruler_start = None
        ruler_end = None
        zoom_center = (frame.shape[1] / 2, frame.shape[0] / 2)
        M = cv2.getRotationMatrix2D(zoom_center, 0, zoom_factor)
        zoomed_frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
        resized_frame = cv2.resize(zoomed_frame, (640, 480))

        cv2.imshow("Camera", resized_frame)

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Frame visualization

class CaptureThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, frame, filename):
        super().__init__()
        assert frame is not None, "Frame is None!"
        assert isinstance(frame, np.ndarray), f"Frame is not ndarray, but {type(frame)}"
        assert frame.size > 0, "Frame is empty!"
        self.frame = frame
        self.filename = filename


    def run(self):
        try:
            print("Running CaptureThread. Saving to:", self.filename)
            if not self.filename.endswith('.png'):
                self.filename += '.png'

            success = cv2.imwrite(self.filename, self.frame)
            print("cv2.imwrite returned:", success)

            if success:
                self.finished.emit(f"Captured frame saved to {self.filename}")
            else:
                self.finished.emit(f"Failed to save frame to {self.filename}")
        except Exception as e:
            print("Exception in CaptureThread:", e)
            self.finished.emit(f"Exception occurred while saving: {e}")


def capture_frame(frame, parent_window=None):
    # ✅ Get real Desktop path
    desktop_path = os.path.join(os.environ["USERPROFILE"], "Desktop")

    # ✅ Pause camera thread
    if hasattr(g, "camera_thread") and g.camera_thread is not None:
        g.camera_thread.pause()

    options = QFileDialog.Options()
    options |= QFileDialog.DontUseNativeDialog

    filename, _ = QFileDialog.getSaveFileName(
        parent_window,
        "Save Frame As",
        os.path.join(desktop_path, "captured_image.png"),
        "PNG files (*.png);;All files (*.*)",
        options=options
    )

    # ✅ Resume camera thread
    if hasattr(g, "camera_thread") and g.camera_thread is not None:
        g.camera_thread.resume()

    if not filename:
        print("Save cancelled")
        return

    if not filename.endswith(".png"):
        filename += ".png"

    try:
        success = cv2.imwrite(filename, frame.copy())
        if success:
            print(f"✅ Image saved to: {filename}")
        else:
            print(f"❌ Failed to save image to: {filename}")
    except Exception as e:
        print(f"❌ Exception while saving: {e}")


def get_histogram_image(image):
    channels = cv2.split(image)
    colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255))
    histogram_image = np.zeros((300, 256, 3), dtype="uint8")  # Size of the histogram image

    for (channel, color) in zip(channels, colors):
        histogram = cv2.calcHist([channel], [0], None, [256], [0, 256])
        cv2.normalize(histogram, histogram, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        for (x, y) in enumerate(histogram):
            cv2.line(histogram_image, (int(x), 300), (int(x), 300 - int(y[0])), color, 1)

    return histogram_image


def adjust_parameters(val=None):
    global r_offset, g_offset, b_offset, brightness, contrast, blur_ksize

    try:
        r_offset = cv2.getTrackbarPos('R offset', 'Camera')
        g_offset = cv2.getTrackbarPos('G offset', 'Camera')
        b_offset = cv2.getTrackbarPos('B offset', 'Camera')
        brightness = cv2.getTrackbarPos('Brightness', 'Camera') - 100
        contrast = cv2.getTrackbarPos('Contrast', 'Camera') / 100.0
        blur_val = cv2.getTrackbarPos('Blur KSize', 'Camera')
        blur_ksize = 2 * blur_val + 1 if blur_val > 0 else 1
    except cv2.error as e:
        # Trackbar probably doesn't exist yet — skip this update
        pass

def render_drawing(frame):
    for draw_polygon, draw_color in drawing_polygons:
        cv2.polylines(frame, [np.array(draw_polygon, dtype=np.int32)], True, draw_color, 5)

    if drawing_closed:
        cv2.polylines(frame, [np.array(drawing_poly_shifted, dtype=np.int32)], True, colors[color_index], 5)
    else:
        if drawing_polygon:
            cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], False, colors[color_index], 5)

            # ✅ Show attractive circle if hovering over a point
            if drawing_highlighted_point:
                cv2.circle(frame, drawing_highlighted_point, attraction_range, (0, 0, 255), 2)


def render_measuring(frame):
    if ruler_start and ruler_end:
        cv2.line(frame, ruler_start, ruler_end, (0, 0, 255), 2)

def render_tracking(display_frame, hidden_frame):
    global poly_shifted, old_center, polygon_profile, tracking, closed
    if closed:
        if tracking:
             # Make sure tracker exists before updating
            if tracker is not None:
                try:
                    success, box = tracker.update(hidden_frame)
                except cv2.error as e:
                    print("⚠️ Tracker update failed:", e)
                    tracking = False
                    return
                if success:
                    new_center = (box[0] + box[2] // 2, box[1] + box[3] // 2)
                    dx, dy = (new_center[0] - old_center[0]) / zoom_factor, (
                            new_center[1] - old_center[1]) / zoom_factor
                    poly_shifted = [(x + dx, y + dy) for (x, y) in poly_shifted]
                    old_center = new_center

                    # Update the polygon_profile with the new coordinates and center
                    center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
                    center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
                    polygon_profile['center'] = (center_x, center_y)
                    polygon_profile['points'] = poly_shifted
                    polygon_profile['edges'] = [np.sqrt((poly_shifted[i][0] - poly_shifted[i - 1][0]) ** 2 + (
                            poly_shifted[i][1] - poly_shifted[i - 1][1]) ** 2) for i in
                                                range(1, len(poly_shifted))]
                    polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0] - poly_shifted[-1][0]) ** 2 + (
                            poly_shifted[0][1] - poly_shifted[-1][
                        1]) ** 2))  # Add the edge between the last and first points
                else:
                    cv2.putText(display_frame, "Tracking failure detected", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5,
                                (0, 0, 255), 4)
            else:
                # Tracker is None — show a warning or skip tracking
                cv2.putText(display_frame, "Tracker not initialized", (100, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        # Draw polygon outline
        if poly_shifted:
            # poly_shifted_zoomed = [(int(x * zoom_factor), int(y * zoom_factor)) for (x, y) in poly_shifted]
            cv2.polylines(display_frame, [np.array(poly_shifted, dtype=np.int32)], True, (0, 255, 0), 5)
    else:
        if polygon:
            for point in polygon:
                if point == highlighted_point:
                    cv2.circle(display_frame, point, attraction_range, (0, 0, 255), 2)
            cv2.polylines(display_frame, [np.array(polygon, dtype=np.int32)], False, (0, 255, 0), 5)


def draw_scale_bar(frame, zoom_factor):
    # Determine the length of the horizontal part of the scale bar in pixels, based on the zoom factor
    scale_bar_length = g.parameters["Camera"]["Scalebar"]

    # Determine the start and end points for the horizontal part of the scale bar
    start_point_horizontal = (20, frame.shape[0] - 20)  # 20 pixels from the left-bottom corner
    end_point_horizontal = (int(start_point_horizontal[0] + scale_bar_length), start_point_horizontal[1])

    # Determine the start and end points for the vertical parts of the scale bar
    start_point_vertical_left = (start_point_horizontal[0], start_point_horizontal[1] - 5)
    end_point_vertical_left = (start_point_horizontal[0], start_point_horizontal[1] + 5)

    start_point_vertical_right = (end_point_horizontal[0], end_point_horizontal[1] - 5)
    end_point_vertical_right = (end_point_horizontal[0], end_point_horizontal[1] + 5)

    # Draw the horizontal line representing the main part of the scale bar
    cv2.line(frame, start_point_horizontal, end_point_horizontal, (0, 0, 255), 2)

    # Draw the vertical lines at both ends of the scale bar
    cv2.line(frame, start_point_vertical_left, end_point_vertical_left, (0, 0, 255), 2)
    cv2.line(frame, start_point_vertical_right, end_point_vertical_right, (0, 0, 255), 2)

    # Add text next to the scale bar indicating its real-world length
    text = f"{np.round(g.parameters['Camera']['Scalebar'] / zoom_factor, 1)} micro"  # Change this according to the real-world length represented by the scale bar
    cv2.putText(frame, text, (end_point_horizontal[0] + 5, end_point_horizontal[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 0, 255), 2) 

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""

"""-------"""
# New codes

class CameraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel("Camera Feed")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: black;")
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.mode = "default"

    def update_image(self, frame):
        if frame is None:
            return
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.label.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.label.setPixmap(scaled_pixmap)


    # --------------------------------------------------------------------
    # Mouse interactions (replacing cv2.EVENT_* callbacks)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            handle_camera_mouse_event(self, event, cv2.EVENT_LBUTTONDOWN)
        elif event.button() == Qt.RightButton:
            handle_camera_mouse_event(self, event, cv2.EVENT_RBUTTONDOWN)

    def mouseMoveEvent(self, event: QMouseEvent):
        handle_camera_mouse_event(self, event, cv2.EVENT_MOUSEMOVE)

    def mouseReleaseEvent(self, event: QMouseEvent):
        handle_camera_mouse_event(self, event, cv2.EVENT_LBUTTONUP)

    def wheelEvent(self, event: QWheelEvent):
        handle_camera_wheel_event(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            handle_camera_mouse_event(self, event, cv2.EVENT_LBUTTONDBLCLK)


def map_qt_event_to_original_coordinates(event: QMouseEvent, widget: CameraWidget):
    label = widget.label
    pixmap = label.pixmap()
    if pixmap is None or pixmap.isNull():
        return -1, -1, event.pos().x(), event.pos().y()

    frame_w = g.original_frame_width
    frame_h = g.original_frame_height
    if frame_w is None or frame_h is None:
        return -1, -1, event.pos().x(), event.pos().y()

    # Use displayed image size (actual pixmap)
    scaled_w = pixmap.width()
    scaled_h = pixmap.height()
    contents = label.contentsRect()
    label_w = contents.width()
    label_h = contents.height()


    x_offset = contents.x() + (label_w - scaled_w) // 2
    y_offset = contents.y() + (label_h - scaled_h) // 2

    x = event.pos().x()
    y = event.pos().y()

    if not (x_offset <= x <= x_offset + scaled_w and
            y_offset <= y <= y_offset + scaled_h):
        return -1, -1, x, y

    # Normalize to scaled image
    x_norm = (x - x_offset) / scaled_w
    y_norm = (y - y_offset) / scaled_h

    # Compute zoomed region size
    zoomed_width = int(frame_w / g.zoom_factor)
    zoomed_height = int(frame_h / g.zoom_factor)

    x_zoomed = int(x_norm * zoomed_width)
    y_zoomed = int(y_norm * zoomed_height)

    x_original = x_zoomed + g.left
    y_original = y_zoomed + g.top

    # Optional manual correction
    x_original += g.manual_x_shift
    y_original += g.manual_y_shift

    return x_original, y_original, x, y

def handle_camera_mouse_event(widget, event: QMouseEvent, event_type: int):
    x_original, y_original, x_click, y_click = map_qt_event_to_original_coordinates(event, widget)
    # cv2.circle(g.frame, (int(x_original), int(y_original)), 5, (0, 255, 0), -1)


    if g.frame is not None:
    # Visual feedback on raw frame and Qt frame
        cv2.circle(g.frame, (x_original, y_original), 5, (0, 0, 255), -1) # raw frame
        cv2.circle(g.Frame, (int(x_click), int(y_click)), 5, (0, 255, 0), -1) # displayed resized frame

    # Dispatch based on mode
    if g.mode == "measuring":
        handle_measuring_mode(event_type, x_original, y_original, event.buttons(), None)
    elif g.mode == "drawing":
        handle_drawing_mode(event_type, x_original, y_original, event.buttons(), None)
    elif g.mode == "tracking":
        handle_tracking_mode(event_type, x_original, y_original, event.buttons(), None)
    elif g.mode == "default":
        handle_default_mode(event_type, x_click, y_click, event.buttons(), None)

def handle_camera_wheel_event(event: QWheelEvent):
    direction = 1 if event.angleDelta().y() > 0 else -1
    if g.mode == "drawing":
        handle_drawing_mode(cv2.EVENT_MOUSEWHEEL, 0, 0, direction, None)
    elif g.mode == "tracking":
        handle_tracking_mode(cv2.EVENT_MOUSEWHEEL, 0, 0, direction, None)

def initialize_camera(gain_value=64):
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    camera.Open()
    nodemap = camera.GetNodeMap()
    
    try:
        pixel_format_node = nodemap.GetNode("PixelFormat")
        available_formats = [str(s) for s in pixel_format_node.GetSymbolics()]
        print("Available pixel formats:", available_formats)

        if "BayerRG8" in available_formats:
            pixel_format_node.SetValue("RGB8")
            print("PixelFormat set to BayerRG8")
        else:
            print("BayerRG8 not available on this camera.")
    except Exception as e:
        print("Could not set PixelFormat:", e)

    try:
        # Try to disable auto gain
        try:
            gain_auto = nodemap.GetNode("GainAuto")
            gain_auto.SetValue("Off")
            # print("GainAuto set to Off")
        except Exception as e:
            print("Could not set GainAuto to Off:", e)

        # Try to set manual gain
        try:
            gain_node = nodemap.GetNode("Gain")
            gain_min = gain_node.GetMin()
            gain_max = gain_node.GetMax()
            gain_value = max(min(gain_value, gain_max), gain_min)
            gain_node.SetValue(gain_value)
            print(f"GainRaw set to {gain_value} (range: {gain_min}–{gain_max})")
        except Exception as e:
            print("Could not set GainRaw:", e)

    except Exception as e:
        print("Failed to configure gain:", e)

    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    if camera.IsGrabbing():
        print("Camera connected successfully")
    else:
        raise Exception("Failed to connect to the camera")

    return camera


class CameraControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()

        self.sliders = {}

        self.add_slider(layout, 'R Offset', 0, 255, 0)
        self.add_slider(layout, 'G Offset', 0, 255, 0)
        self.add_slider(layout, 'B Offset', 0, 255, 0)
        self.add_slider(layout, 'Brightness', 0, 200, 100)
        self.add_slider(layout, 'Contrast', 0, 300, 100)
        self.add_slider(layout, 'Sharpness', 0, 7, 0)
        self.add_slider(layout, 'Gamma', 10, 300, 150)  # Scale 10–300, default 150 → gamma 1.5


        self.setLayout(layout)

    def add_slider(self, layout, name, min_val, max_val, default_val):
        label = QLabel(f"{name}: {default_val}")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(lambda val, l=label, n=name: self.update_label(val, l, n))

        layout.addWidget(label)
        layout.addWidget(slider)
        self.sliders[name] = slider

    def update_label(self, val, label, name):
        label.setText(f"{name}: {val}")

        if name == 'R Offset':
            g.r_offset = val
        elif name == 'G Offset':
            g.g_offset = val
        elif name == 'B Offset':
            g.b_offset = val
        elif name == 'Brightness':
            g.brightness = val - 100
        elif name == 'Contrast':
            g.contrast = val * 0.01
        elif name == 'Sharpness':
            g.blur_ksize = 2 * val + 1 if val > 0 else 0
        elif name == 'Gamma':
            g.gamma = val

class CameraThread(QThread):

    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.camera = None
        self.paused = False

    def stop(self):
        self.running = False
        if self.camera and self.camera.IsGrabbing():
            self.camera.StopGrabbing()

    def run(self):
        global frame, top, left, zoom_factor
        self.camera = initialize_camera(gain_value=64)
        # Force the camera to output Bayer color data (needed for acA1920-40uc)
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        while self.running and self.camera.IsGrabbing():
            if self.paused:
                self.msleep(100)
                continue

            grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if not grabResult.GrabSucceeded():
                continue

            image = converter.Convert(grabResult)
            frame = image.GetArray()
            frame = apply_color_correction(frame)
            display_frame = frame.copy()
            g.frame = frame

            # === Zooming ===
            if g.original_frame_width is None or g.original_frame_height is None:
                g.original_frame_width, g.original_frame_height = frame.shape[1], frame.shape[0]

            zoomed_height = int(frame.shape[0] / zoom_factor)
            zoomed_width = int(frame.shape[1] / zoom_factor)

            top = max(0, min(top, frame.shape[0] - zoomed_height))
            left = max(0, min(left, frame.shape[1] - zoomed_width))

            zoomed_region = display_frame[top:top + zoomed_height,
                                          left:left + zoomed_width]

            # Apply RGB offset and contrast adjustments
            # Update display frame with RGB offset
            display_frame[..., 0] = cv2.add(display_frame[..., 0], g.b_offset)  # Blue
            display_frame[..., 1] = cv2.add(display_frame[..., 1], g.g_offset)  # Green
            display_frame[..., 2] = cv2.add(display_frame[..., 2], g.r_offset)  # Red


            # Draw overlays depending on mode
            render_drawing(display_frame)
            if g.mode == "tracking":
                render_tracking(display_frame, frame)
            elif g.mode == "measuring":
                render_measuring(display_frame)

            draw_frame(display_frame)

            # Convert the frame to grayscale for processing
            # gray = cv2.cvtColor(display_frame, cv2.COLOR_BGR2GRAY)

            # Apply brightness and contrast
            brighted = cv2.convertScaleAbs(zoomed_region, alpha=g.contrast, beta=g.brightness)

            # Apply Gaussian blur
            if g.blur_ksize >= 1:
                blurred = cv2.GaussianBlur(brighted, (g.blur_ksize, g.blur_ksize), 0)
            else:
                blurred = brighted

            # Convert back to BGR for display or further processing
            processed_frame = blurred
            
            
            # === Resize and add histogram ===
            # resized_frame = cv2.resize(zoomed_region, (640, 480))
            # histogram_image = get_histogram_image(resized_frame)
            # histogram_image = cv2.resize(histogram_image, (histogram_image.shape[1], resized_frame.shape[0]))
            # combined_image = np.concatenate((resized_frame, histogram_image), axis=1)

            # draw_scale_bar(combined_image, zoom_factor)

            self.frame_ready.emit(processed_frame)
            grabResult.Release()

        def pause(self):
            self.paused = True

        def resume(self):
            self.paused = False

        self.camera.StopGrabbing()