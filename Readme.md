# GUI User Guide

## Install

Optional:
```cmd
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate
```
Then:
```cmd
pip install -r requirements.txt
```

## Run
```cmd
python ./obc_gui.py
```

## Overview 
### UI Layout
- **Recommended**: Use a terminal emulator (e.g., Linux Terminal, Windows Terminal, iTerm2) rather than the default Windows CMD.

- **Default Size**: 80×24 (the UI will adapt if you resize).

- **Header Section**:
  + ***Size***: Displays the current terminal dimensions.
  + ***Datetime***: Shows the current timestamp (updated every second).
  + ***Status***: Shows one of:
    + ***Active*** (application running, no serial connection yet)
    + ***Connected*** (serial port is open to the device)

- **Menu** (Left Panel):
  + Use `Up` / `Down` arrow keys to navigate between items.
  + Press `Enter` to open the selected menu.
  + Press `Esc` to return to the main menu from any submenu.
  + Press `Ctrl+C` to exit the application.

- **Center Panel**:
  + ***Displays either***:
    + ***Information View*** (details and fields for the selected submenu), or
    + ***Terminal View*** (raw command‐line interface, see “Terminal” below).

  + ***Right Panel*** (“Send” / “Recv”):
    + ***Send***: TBD
    + ***Recv***: TBD

- **Log Bar** (Bottom):
  + Displays one line of console/log messages (e.g., “Config saved!”, “Error: …”).
### Function - Menu subitems
- ***PreSetup***: Configure the serial‐port connection (port name + baud rate).
- ***Config***: Set sampling parameters `SampleRate[Sample/s]`, `SampleSet[Sample]` 
- ***Tracking***: TBD
- ***Manual***: Manually control the laser, read current, and read photodiode.
- ***Terminal***: Raw command‐line interface for sending arbitrary commands over UART.
- ***Option***: TBD
- ***Quit***: Exit the application.


## Usage:
**1. First of all - PreSetup**
- From the main menu, navigate to `PreSetup` and press `Enter`.
Use the Up/Down arrows to highlight each field:

- Type Connect: TBD (Default `Serial`)

- Port: Press Enter to scan for available COM ports. If multiple ports are found, each Enter will cycle through them.
- BaudRate: Type a numeric value (e.g., 9600, 115200). Use Backspace to correct digits.

- Navigate down to [ Connect ] and press Enter:
  + If successful, Status changes to Connected and a message appears in the Log Bar (e.g., “COM3 Opened, Baudrate: 115200”).
  + If it fails (invalid port or baud rate), an error message appears in the Log Bar.

<p align="center">
  <img src="image.png" alt="alt text" width="50%"/>
</p>

**2. Second step - Config Sample**
- Press `Esc` to return to the main menu.
- Navigate to `Config` and press `Enter`.
You will see two fields:
  + SampleSet [Sample]
  + SampleRate [Sample/s]
- Type numeric values (e.g., 100 for SampleSet, 500 for SampleRate).
- Use Backspace to delete digits.
- Navigate down to `[ Apply ]` and press `Enter`:
  + If no serial connection is established, Log Bar shows: “Error: Communication not established.”
  + If connected, the command `sp_set_rate <SampleRate> <SampleSet>` is sent over UART, then:
    + The JSON file Config.json is updated,
    + Log Bar shows “Config OK!”
    + You return to the main menu.

<p align="center">
  <img src="image-1.png" alt="alt text" width="50%"/>
</p>

**3. Main step - Control and Monitor Data**
- 1. Press `Esc` to return to the main menu.
- 2. Navigate to `Manual` and press `Enter`.
You will see several fields. Use Up/Down and Enter to:
      + Toggle `ADC Peripheral` between `External/Internal`.
      + Toggle `Laser Type` between `Internal/External`.
      + Edit `Laser Index` (integer from 0 to 36).
      + Edit `Laser DAC` (integer from 0 to 100).
      + Toggle `Current Type` between `Internal/External`.
      + Edit `PhotoDiode Index` (integer from 0 to 36).
- 3. Once you set these values, use Up/Down to highlight one of the three “Send” commands:
      + `$: > [Send – Laser Set]`: Sends    `set_laser <int/ext> <LaserIndex> <LaserDAC>` over UART.
      + `$: > [Send – Current Get]`: Sends `get_current <int/ext>` over UART.
      + `$: > [Send – PhotoDiode Get]` (three‐step process):
        + `Step 0 – [Send – PhotoDiode Set]`: Sends `sp_set_pd <PhotoDiodeIndex>` over UART.
        + `Step 1 – [Send – Trigger Read]`: Sends `sp_trig` over UART.
        + `Step 2 – [Send – PhotoDiode Get]`: 
          + Sets up a data‐logging file at `./Data/Index<Index>_<Timestamp>.log`.
          + Sends `sp_get_buf_c` over UART.
          + Device begins streaming photodiode data into that file (close it to stop).
      + If any UART send fails (no connection), Log Bar shows `“Error: Communication not established.”`
- 4. After each successful send, a `“Sent: OK”`message appears in the `Log Bar`.
- 5. **To stop photodiode logging, go back to `Step 2 – [Send – PhotoDiode Get]`, press Enter again to toggle “Close,” which closes the data file and stops logging.**

<p align="center">
  <img src="image-2.png" alt="alt text" width="50%"/>
</p>


**4. Terminal - Raw Command‐Line Interface**
- Press `Esc` to return to the main menu.
- Navigate to `Terminal` and press `Enter`.
  You see a console with:
    - **Log area (top)**: Scrolls recent commands and responses (up to N lines).
    - **Input area (bottom, titled `“Input”`)**: One‐line prompt `>>>` .
- Type any valid command string and press `Enter`.
- All raw UART traffic (both send and receive) is also saved to:
  - Application log: `./Log/Log_<Timestamp>.log`
  - Realtime display in the `Terminal` window.

<p align="center">
  <img src="image-3.png" alt="alt text" width="50%"/>
</p>
