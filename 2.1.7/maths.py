"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Modules

from scipy.optimize import fsolve
import numpy as np
import cv2

"""-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"""
# Functions

def solve_for_r(x1, y1, x2, y2, theta):
    # Equations to be solved
    def equations(vars):
        r, theta0 = vars
        eq1 = (x2 - x1) - r * (np.cos(theta + theta0) - np.cos(theta0))
        eq2 = (y2 - y1) - r * (np.np.sin(theta + theta0) - np.sin(theta0))
        return [eq1, eq2]

    # Initial guess for r and theta0
    initial_guess = [1, 0]

    # Solve for r and theta0
    solution = fsolve(equations, initial_guess)

    r_solution, theta0_solution = solution
    return r_solution, theta0_solution

class PID:
    def __init__(self, Kp, Ki, Kd):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_error = 0
        self.integral = 0

    def compute(self, setpoint, measured_value):
        error = setpoint - measured_value
        self.integral += error
        derivative = error - self.prev_error
        output = self.Kp*error + self.Ki*self.integral + self.Kd*derivative
        self.prev_error = error
        return output
    
def get_roi(gray_img):
    h, w = gray_img.shape
    x1, y1 = int(w * 0.35), int(h * 0.35)
    x2, y2 = int(w * 0.65), int(h * 0.65)
    return x1, y1, x2, y2
    
def sobel_variance_focus_measure(img, ksize=3):
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x1, y1, x2, y2 = get_roi(img)
    roi = img[y1:y2, x1:x2]
    # cv2.imshow('ROI', roi)
    # cv2.waitKey(1)  # or cv2.waitKey(0) if you want to pause until a key is pressed
    sobelx = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=ksize)
    sobely = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=ksize)
    sobel = np.hypot(sobelx, sobely)
    score = np.var(sobel)
    return score

image_analysis_log = None