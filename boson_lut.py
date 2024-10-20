import cv2
import numpy as np
import argparse
import datetime
import tkinter as tk
from tkinter import Button, Label, Frame, OptionMenu, StringVar
from PIL import Image, ImageTk
import os
import pyudev

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

# Camera resolution settings
CAMERA_RESOLUTIONS = {
    'BOSON': (640, 512),
    'LEPTON3': (160, 120),
    'LEPTON2': (80, 60)
}

# Function to detect available FLIR cameras using pyudev


def get_video_devices_for_flir():
    context = pyudev.Context()
    flir_devices = []

    # Iterate over all video devices
    for device in context.list_devices(subsystem='video4linux'):
        parent = device.find_parent(subsystem='usb', device_type='usb_device')
        if parent is None:
            continue
        vendor_id = parent.properties.get('ID_VENDOR_ID')
        product_id = parent.properties.get('ID_MODEL_ID')
        model = parent.properties.get('ID_MODEL', '')

        # Check if this is the FLIR Boson camera based on Vendor ID and Product ID
        if vendor_id == '09cb':  # FLIR vendor ID
            print(
                f"Found FLIR Boson camera: {model}, Device: {device.device_node}")
            flir_devices.append(device.device_node)
        # Check if this is the FLIR Lepton (Cubeternet WebCam) based on Vendor ID and Product ID
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

# Function to apply LUT to a video frame


def apply_lut(frame, lut_name):
    if lut_name not in LUTS:
        raise ValueError(f"Unsupported LUT: {lut_name}")

    # Get the OpenCV LUT or custom LUT
    colormap = LUTS[lut_name]()

    if isinstance(colormap, np.ndarray):
        # Apply custom LUT using LUT transformation
        colored_frame = cv2.LUT(frame, colormap)
    else:
        # Apply built-in OpenCV colormap
        colored_frame = cv2.applyColorMap(frame, colormap)
    return colored_frame

# Main function


def main(lut_name, camera_type='BOSON'):
    available_cameras = get_video_devices_for_flir()
    if not available_cameras:
        print("No FLIR cameras detected.")
        return

    current_camera_index = available_cameras[0]

    # Capture video from the initial camera
    cap = cv2.VideoCapture(current_camera_index, cv2.CAP_V4L2)

    if not cap.isOpened():
        print(f"Error: Could not open video device {current_camera_index}")
        return
        print(f"Error: Could not open video device {current_camera_index}")
        return

    # Set frame properties based on the camera type
    if camera_type in CAMERA_RESOLUTIONS:
        frame_width, frame_height = CAMERA_RESOLUTIONS[camera_type]
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    else:
        print(
            f"Warning: Unknown camera type '{camera_type}'. Using default resolution.")
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Initialize recording variables
    out = None
    recording = False

    # Create the Tkinter window
    root = tk.Tk()
    root.title("Thermal Camera Control")

    # Control frame for buttons and LUT selection
    control_frame = Frame(root)
    control_frame.pack(pady=5)

    # LUT selection dropdown
    lut_var = StringVar(root)
    lut_var.set(lut_name)
    if lut_name not in LUTS:
        print(f"Error: Unsupported LUT '{lut_name}'. Defaulting to 'REDHOT'.")
        lut_var.set('REDHOT')
    lut_menu = OptionMenu(control_frame, lut_var, *sorted(LUTS.keys()))
    lut_menu.pack(side="left", padx=5)

    # Camera selection dropdown
    camera_var = StringVar(root)
    camera_var.set(f"Camera {current_camera_index}")
    camera_menu = OptionMenu(control_frame, camera_var,
                             *[f"Camera {device}" for device in available_cameras])
    camera_menu.pack(side="left", padx=5)

    def switch_camera():
        nonlocal cap, current_camera_index
        selected_camera = camera_var.get().split()[-1]
        if selected_camera != current_camera_index:
            cap.release()
            current_camera_index = selected_camera
            cap = cv2.VideoCapture(current_camera_index, cv2.CAP_V4L2)
            if not cap.isOpened():
                print(
                    f"Error: Could not open video device {current_camera_index}")
                return
            # Set frame properties again after switching
            if camera_type in CAMERA_RESOLUTIONS:
                frame_width, frame_height = CAMERA_RESOLUTIONS[camera_type]
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    camera_menu.config(command=lambda _: switch_camera())

    # Record and Exit buttons
    Button(control_frame, text="Start/Stop Recording",
           command=lambda: toggle_recording()).pack(side="left", padx=5)
    Button(control_frame, text="Exit Program",
           command=lambda: exit_program()).pack(side="left", padx=5)

    # Video frame label
    video_label = Label(root)
    video_label.pack()

    def update_frame():
        nonlocal recording, out
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from video stream")
            root.after(50, update_frame)
            return

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
        root.after(10, update_frame)

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

    def exit_program():
        cap.release()
        if out:
            out.release()
        root.destroy()

    # Start updating the video frame
    update_frame()

    # Start the Tkinter main loop
    root.mainloop()

    # Release resources
    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply a false-color LUT to a video stream from a thermal camera.")
    parser.add_argument('lut_name', type=str, nargs='?', default='REDHOT', choices=sorted(LUTS.keys()),
                        help="Name of the LUT to apply. Available options: " + ", ".join(sorted(LUTS.keys())) + ". Default is 'REDHOT'.")
    parser.add_argument('--camera_type', type=str, default='BOSON', choices=['BOSON', 'LEPTON3', 'LEPTON2'],
                        help="Type of camera being used ('BOSON', 'LEPTON3', 'LEPTON2'). Default is 'BOSON'.")

    args = parser.parse_args()

    main(args.lut_name, args.camera_type)
