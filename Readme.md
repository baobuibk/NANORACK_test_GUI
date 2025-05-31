# RaspiGUI User Guide

RaspiGUI is a terminal-based user interface for controlling and configuring laser systems via a serial connection. This guide explains how to navigate the interface and configure settings in the **SControl** and **Laser** menus.

## Navigation

- **Menu Panel**: Located on the left side of the interface, it lists available options: **SControl**, **Laser**, **Tracking**, **Logs**, and **Quit**.
- **Controls**:
  - Use the **Up** or **Down** arrow keys to move between menu items.
  - Press **Enter** to enter the selected menu.
  - Press **Esc** to return to the main menu from a submenu.
  - Press **Ctrl+C** to exit the application.

## SControl Settings

The **SControl** menu allows you to configure system services and serial communication settings.

- **Fields**:
  - **SSH Service**: Enable or disable SSH service.
  - **VNC Service**: Enable or disable VNC service.
  - **Set laser**: Select laser type (`int` or `ext`).
  - **Get current**: Select current type (`int` or `ext`).
  - **Photodiode Get**: Enable or disable photodiode data retrieval.
  - **Serial Port**: Enable or disable serial communication.
  - **COM**: Select the serial port for communication.

- **Controls**:
  - Use **Up** or **Down** arrow keys to highlight a field.
  - Press **Enter** on fields like **SSH Service**, **VNC Service**, **Serial Port**, **Set laser**, **Get current**, or **Photodiode Get** to toggle between `Enabled` and `Disabled` or switch types (`int`/`ext`).
  - For the **COM** field, press **Enter** to cycle through available serial ports (e.g., COM1, COM2).
  - After configuring, move to **[ Apply ]** using **Up** or **Down**, then press **Enter** to save changes and apply settings.

## Laser Settings

The **Laser** menu allows configuration of laser parameters and photodiode settings.

- **Fields**:
  - **ADC type**: Select ADC type (`int` or `ext`).
  - **Laser set**: Enable or disable laser control.
  - **Laser type**: Select laser type (`int` or `ext`).
  - **Laser index**: Enter the laser index (numeric input).
    - If **Laser type** is `int`: Range is **0 to 36**.
    - If **Laser type** is `ext`: Range is **0 to 8**.
  - **DAC voltage**: Enter the DAC voltage (numeric input, range **0 to 100**).
  - **Get current**: Enable or disable current retrieval.
  - **Get current type**: Select current type (`int` or `ext`).
  - **Photodiode Get**: Enable or disable photodiode data retrieval.
  - **Photodiode index**: Enter the photodiode index (numeric input, range **0 to 36**).

- **Controls**:
  - Use **Up** or **Down** arrow keys to highlight a field.
  - Press **Enter** on fields like **ADC type**, **Laser set**, **Laser type**, **Get current**, **Get current type**, or **Photodiode Get** to toggle between `Enabled`/`Disabled` or switch types (`int`/`ext`).
  - For numeric fields (**Laser index**, **DAC voltage**, **Photodiode index**):
    - Highlight the field, then type numbers (0-9) to input a value.
    - Use **Backspace** to delete digits.
    - **Laser index** is restricted based on **Laser type**:
      - `int`: 0-36.
      - `ext`: 0-8.
    - **DAC voltage**: 0-100.
    - **Photodiode index**: 0-36.
  - After configuring, move to **[ Apply ]** using **Up** or **Down**, then press **Enter** to save changes and send commands to the device.

## Notes

- Ensure a valid serial port is selected and enabled in **SControl** before sending commands in **Laser** or **Logs**.
- The **Data** panel (right side) displays serial communication logs (e.g., sent commands, received responses) when not in the **Logs** menu.
- In the **Logs** menu, you can manually enter commands to send via serial (except `help`, which displays supported commands).

For issues or additional commands, refer to the project documentation or contact the development team.