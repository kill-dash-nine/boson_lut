# Boson LUT Script

## Overview
This script is used to apply false-color Look-Up Tables (LUTs) to a video stream from a FLIR thermal camera (such as FLIR Boson or FLIR Lepton). The script also provides a GUI using Tkinter for user interaction, where users can select different LUTs and control video recording.

The primary features of the script include:
- Detection of available FLIR cameras.
- Application of various predefined or custom LUTs to thermal video streams.
- Video recording capability.
- A user-friendly GUI for camera and LUT selection.

## Required Python Modules
The following Python modules are required to run this script:
- `opencv-python`
- `numpy`
- `Pillow`
- `pyudev`
- `tkinter`
- `argparse`

To install the required modules, run the following command:
```sh
pip install opencv-python numpy Pillow pyudev
```

Note: `tkinter` is usually included with the standard Python installation.

## Usage
The script can be run from the command line and provides various command line options to customize the behavior. Below are the available options.

### Command Line Options
- `lut_name` (positional argument): The name of the LUT to apply. Available options include:
  - `WHITEHOT`, `BLACKHOT`, `REDHOT`, `RAINBOW`, `OCEAN`, `LAVA`, `ARCTIC`, `GLOBOW`, `GRADEDFIRE`, `INSTALERT`, `SPRING`, `SUMMER`, `COOL`, `HSV`, `PINK`, `HOT`, `MAGMA`, `INFERNO`, `PLASMA`, `VIRIDIS`, `CIVIDIS`, `ISOTHERM_RED`, `ISOTHERM_GREEN`, `ISOTHERM_BLUE`.
  - Default value: `REDHOT`.
- `--camera_type` (optional argument): The type of camera being used. Options include:
  - `BOSON`, `LEPTON3`, `LEPTON2`.
  - Default value: `BOSON`.

### Example Usage
```sh
python boson_lut.py REDHOT --camera_type BOSON
```
This command runs the script, applies the `REDHOT` LUT, and uses the `BOSON` camera type.

## Features
- **Thermal Camera Detection**: Automatically detects connected FLIR cameras using `pyudev`.
- **GUI Controls**: A GUI interface using Tkinter allows users to:
  - Select different LUTs.
  - Switch between detected cameras.
  - Start or stop video recording.
  - Exit the application.
- **Custom LUTs**: The script also allows the application of custom LUTs, such as `ISOTHERM_RED`, `ISOTHERM_GREEN`, and `ISOTHERM_BLUE`.

## Set USB Permissions
We faced an issue with the application not having permission to access the FLIR Boson USB device. To resolve this, we updated udev rules:

1. **Create a Udev Rule for the FLIR Device**:
   ```bash
   sudo nano /etc/udev/rules.d/99-flir-boson.rules
   ```

2. **Add the Following Line** (to grant access to the USB device):
   ```bash
   SUBSYSTEM=="usb", ATTRS{idVendor}=="09cb", ATTRS{idProduct}=="4007", MODE="0666"
   ```

   **Example `99-flir-boson.rules` file**:
   ```
   # Udev rule to grant permissions for FLIR Boson USB device
   SUBSYSTEM=="usb", ATTRS{idVendor}=="09cb", ATTRS{idProduct}=="4007", MODE="0666"
   ```

3. **Reload Udev Rules**:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

   **Alternative Command** (using device paths):
   ```bash
   sudo udevadm trigger /dev/bus/usb/*
   ```

## Notes
- Ensure that your system has access to the appropriate video devices, and that you have permissions to access them.
- The script uses OpenCV for video capture and processing, and Tkinter for GUI management.
- The FLIR cameras must be connected to the system before running the script.

## License
This project is licensed under the MIT License.

