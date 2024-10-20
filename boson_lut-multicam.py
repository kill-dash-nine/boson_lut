import cv2
import numpy as np
import argparse
import datetime
import tkinter as tk
from tkinter import Button, Label, Frame, OptionMenu, StringVar, Toplevel
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import os
import pyudev
import threading
import time

# Define the available LUTs based on the definitions from the C++ code
LUTS = {
    'WHITEHOT': lambda: cv2.COLORMAP_BONE,
    'BLACKHOT': lambda: cv2.COLORMAP_JET,
    'REDHOT': lambda: cv2.COLORMAP_HOT,
    'RAINBOW': lambda: cv2.COLORMAP_RAINBOW,
    'OCEAN': lambda: cv2.COLORMAP_OCEAN,
    'LAVA': lambda: cv2.COLORMAP_PINK,
    'ARCTIC': lambda: cv2.COLORMAP_WINTER,
    'GLOBOW': lambda: cv2.COLORMAP_PARULA,
    'GRADEDFIRE': lambda: cv2.COLORMAP_AUTUMN,
    'INSTALERT': lambda: cv2.COLORMAP_SUMMER,
    'SPRING': lambda: cv2.COLORMAP_SPRING,
    'SUMMER': lambda: cv2.COLORMAP_SUMMER,
    'COOL': lambda: cv2.COLORMAP_COOL,
    'HSV': lambda: cv2.COLORMAP_HSV,
    'PINK': lambda: cv2.COLORMAP_PINK,
    'HOT': lambda: cv2.COLORMAP_HOT,
    'MAGMA': lambda: cv2.COLORMAP_MAGMA,
    'INFERNO': lambda: cv2.COLORMAP_INFERNO,
    'PLASMA': lambda: cv2.COLORMAP_PLASMA,
    'VIRIDIS': lambda: cv2.COLORMAP_VIRIDIS,
    'CIVIDIS': lambda: cv2.COLORMAP_CIVIDIS,
    'ISOTHERM_RED': lambda: create_custom_lut('red', 32),
    'ISOTHERM_GREEN': lambda: create_custom_lut('green', 32),
    'ISOTHERM_BLUE': lambda: create_custom_lut('blue', 32)
}

# Define step values
color_gradient_step = 0

# Camera resolution settings
CAMERA_RESOLUTIONS = {
    'BOSON': (640, 512),
    'LEPTON3': (160, 120),
    'LEPTON2': (80, 60)
}

# Threading lock to prevent resource conflicts
camera_lock = threading.Lock()

# Function to detect available FLIR cameras using pyudev


def get_video_devices_for_flir():
    context = pyudev.Context()
    flir_devices = []

    # Iterate over all video devices
    for device in context.list_devices(subsystem='video4linux'):
        parent = device.find_parent(subsystem='usb', device_type='usb_device')
        if parent is not None:
            vendor_id = parent.properties.get('ID_VENDOR_ID')
            product_id = parent.properties.get('ID_MODEL_ID')
            model = parent.properties.get('ID_MODEL', '')

            # Check if this is the FLIR Boson camera based on Vendor ID and Product ID
            if vendor_id == '09cb':  # FLIR vendor ID
                print(
                    f"Found FLIR Boson camera: {model}, Device: {device.device_node}")
                flir_devices.append(device.device_node)
            # Check if this is the FLIR Lepton (Cubeternet WebCam) based on Vendor ID and Product ID
            # Cubeternet WebCam (FLIR Lepton)
            elif vendor_id == '1e4e' and product_id == '0100':
                print(
                    f"Found FLIR Lepton camera (Cubeternet WebCam): {model}, Device: {device.device_node}")
                flir_devices.append(device.device_node)

    if not flir_devices:
        print("FLIR camera not found")
    return flir_devices

# Function to create a custom LUT using predefined color data


def create_custom_lut(color, color_gradient_step):
    if color_gradient_step <= 0:
        raise ValueError("color_gradient_step must be greater than 0.")
    """
    Create a custom LUT using predefined color data from the provided image.
    :param color: The color to use for the gradient ('red', 'green', 'blue').
    :return: Custom LUT as a numpy array.
    """
    # Define colors based on the provided image: black to white, then dark color to light color
    if color == 'red':
        gradient_colors = ((0, 0, 64), (0, 0, 255), color_gradient_step)
    elif color == 'green':
        gradient_colors = ((0, 64, 0), (0, 255, 0), color_gradient_step)
    elif color == 'blue':
        gradient_colors = ((64, 0, 0), (255, 0, 0), color_gradient_step)
    else:
        raise ValueError(
            "Unsupported color for LUT creation. Supported colors are 'red', 'green', and 'blue'.")

    BLACK_TO_WHITE_STEP = 256 - color_gradient_step
    black_to_white = np.linspace(
        (0, 0, 0), (255, 255, 255), BLACK_TO_WHITE_STEP).astype(np.uint8)
    color_gradient = np.linspace(*gradient_colors).astype(np.uint8)
    custom_colors = np.concatenate((black_to_white, color_gradient))

    # Ensure we have exactly 256 colors by interpolating if necessary
    if len(custom_colors) != 256:
        custom_colors = np.linspace(
            custom_colors[0], custom_colors[-1], 256, dtype=np.uint8)

    # Create a custom LUT with 256 entries
    custom_lut = custom_colors.reshape((256, 1, 3))
    return custom_lut


def apply_lut(frame, lut_name):
    """
    Apply a false-color LUT to the given video frame.
    :param frame: The input video frame.
    :param lut_name: Name of the LUT to apply.
    :return: False-colored frame.
    """
    if lut_name.upper() not in LUTS:
        raise ValueError(f"Unsupported LUT: {lut_name}")

    # Get the OpenCV LUT or custom LUT
    colormap = LUTS[lut_name.upper()]()

    if isinstance(colormap, np.ndarray):
        # Apply custom LUT using LUT transformation
        colored_frame = cv2.LUT(frame, colormap)
    else:
        # Apply built-in OpenCV colormap
        colored_frame = cv2.applyColorMap(frame, colormap)
    return colored_frame


def create_camera_window(camera_index, lut_name, camera_type):
    retries = 3
    cap = None

    # Retry logic for opening the camera
    while retries > 0:
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if cap.isOpened():
            break
        else:
            print(
                f"Warning: Could not open video device {camera_index}. Retrying...")
            retries -= 1
            time.sleep(1)

    if not cap or not cap.isOpened():
        print(
            f"Error: Could not open video device {camera_index} after multiple attempts.")
        return

    print(f"Successfully opened camera: {camera_index}")

    # Set frame properties based on the camera type
    if camera_type in CAMERA_RESOLUTIONS:
        frame_width, frame_height = CAMERA_RESOLUTIONS[camera_type]
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    else:
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Create the Tkinter window
    camera_window = Toplevel()
    camera_window.title(f"Camera {camera_index}")

    video_label = Label(camera_window)
    video_label.pack()

    def update_frame():
        with camera_lock:
            ret, frame = cap.read()

        if not ret:
            print(
                f"Error: Could not read frame from video stream (Camera {camera_index})")
            camera_window.after(100, update_frame)  # Retry after a short delay
            return

        # Apply LUT
        colored_frame = apply_lut(frame, lut_name)

        # Convert the frame to an image that Tkinter can use
        img = cv2.cvtColor(colored_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)

        # Schedule the next frame update
        camera_window.after_idle(update_frame)

    update_frame()

    # Handle window close event
    def on_close():
        with camera_lock:
            cap.release()
        camera_window.destroy()

    camera_window.protocol("WM_DELETE_WINDOW", on_close)
    camera_window.after_idle(update_frame)


def main():
    available_cameras = get_video_devices_for_flir()

    if not available_cameras:
        print("No FLIR cameras detected.")
        return

    current_camera_index = available_cameras[0]
    camera_type = 'BOSON'  # Assuming BOSON as default, adjust as needed

    # Create the Tkinter window
    root = tk.Tk()
    root.title("Thermal Camera Control")

    # Control frame for buttons and LUT selection
    control_frame = Frame(root)
    control_frame.pack(pady=5)

    # LUT selection dropdown
    lut_var = StringVar(root)
    lut_var.set('WHITEHOT')
    lut_menu = OptionMenu(control_frame, lut_var, *sorted(LUTS.keys()))
    lut_menu.pack(side="left", padx=5)

    # Camera selection dropdown
    camera_var = StringVar(root)
    camera_var.set(f"Camera {current_camera_index}")
    camera_menu = OptionMenu(control_frame, camera_var,
                             *[f"Camera {device}" for device in available_cameras])
    camera_menu.pack(side="left", padx=5)

    # Use trace to call switch_camera when the camera selection changes
    camera_var.trace_add('write', lambda *args: switch_camera())

    def switch_camera():
        nonlocal current_camera_index, cap
        selected_camera = camera_var.get().split()[-1]
        if selected_camera != current_camera_index:
            with camera_lock:
                cap.release()
            current_camera_index = selected_camera
            retries = 3
            while retries > 0:
                cap = cv2.VideoCapture(current_camera_index, cv2.CAP_DSHOW)
                if cap.isOpened():
                    break
                else:
                    print(
                        f"Warning: Could not open video device {current_camera_index}. Retrying...")
                    retries -= 1
                    time.sleep(1)
            if not cap or not cap.isOpened():
                print(
                    f"Error: Could not open video device {current_camera_index} after multiple attempts.")
                return
            # Set frame properties again after switching
            if camera_type in CAMERA_RESOLUTIONS:
                frame_width, frame_height = CAMERA_RESOLUTIONS[camera_type]
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    # Record and Exit buttons
    Button(control_frame, text="Start/Stop Recording",
           command=lambda: toggle_recording()).pack(side="left", padx=5)
    Button(control_frame, text="Exit Program",
           command=lambda: exit_program()).pack(side="left", padx=5)

    # Flip buttons
    Button(control_frame, text="Flip Horizontal",
           command=lambda: toggle_flip('horizontal')).pack(side="left", padx=5)
    Button(control_frame, text="Flip Vertical",
           command=lambda: toggle_flip('vertical')).pack(side="left", padx=5)

    # Open windows for each camera
    Button(control_frame, text="Open All Cameras",
           command=lambda: open_all_cameras()).pack(side="left", padx=5)

    # Video frame label
    video_label = Label(root)
    video_label.pack()

    cap = cv2.VideoCapture(current_camera_index)
    if not cap.isOpened():
        print(f"Error: Could not open video device {current_camera_index}")
        return

    if camera_type in CAMERA_RESOLUTIONS:
        frame_width, frame_height = CAMERA_RESOLUTIONS[camera_type]
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    else:
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    recording = False
    out = None
    flip_horizontal = False
    flip_vertical = False

    def update_frame():
        nonlocal recording, out, flip_horizontal, flip_vertical
        with camera_lock:
            ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from video stream")
            root.after(100, update_frame)  # Retry after a short delay
            return

        # Apply flipping if enabled
        if flip_horizontal:
            frame = cv2.flip(frame, 1)
        if flip_vertical:
            frame = cv2.flip(frame, 0)

        # Apply LUT
        current_lut = lut_var.get()
        colored_frame = apply_lut(frame, current_lut)

        # Write the frame to the output file if recording
        if recording and out:
            out.write(colored_frame)

        # Convert the frame to an image that Tkinter can use
        img = cv2.cvtColor(colored_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)

        # Schedule the next frame update
        root.after_idle(update_frame)

    def toggle_recording():
        nonlocal recording, out
        if not recording:
            # Start recording
            now = datetime.datetime.now()
            output_file = f"flir-{now.strftime('%M%H-%d%m%y')}.avi"
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(output_file, fourcc,
                                  20.0, (frame_width, frame_height))
            recording = True
            print(f"Started recording to {output_file}")
        else:
            # Stop recording
            recording = False
            if out:
                out.release()
                out = None
            print("Stopped recording")

    def toggle_flip(axis):
        nonlocal flip_horizontal, flip_vertical
        if axis == 'horizontal':
            flip_horizontal = not flip_horizontal
        elif axis == 'vertical':
            flip_vertical = not flip_vertical

    def open_all_cameras():
        threads = []
        for camera in available_cameras:
            thread = threading.Thread(target=create_camera_window, args=(
                camera, lut_var.get(), camera_type))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

    def exit_program():
        with camera_lock:
            cap.release()
        root.destroy()

    update_frame()
    root.mainloop()


if __name__ == "__main__":
    main()
