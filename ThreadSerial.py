import serial
import serial.tools.list_ports
import threading
import time

# Dummy functions for callbacks
def dummy_func():
    return True

def dummy_func_no_arg():
    return True


def dummy_func2(p1, p2):
    return True

def dummy_func3(p1, p2, p3):
    return True

def dummy_func4(p1, p2, p3, p4):
    return True

class ThreadSerial:
    def __init__(self, port=None, baudrate=115200, timeout=2):
        """Initialize ThreadSerial with optional port, baudrate, and timeout."""
        self.close = False
        self.serial = None
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        # Callback functions
        self.port_connection_found_callback = dummy_func3  # port, serial
        self.port_read_callback = dummy_func4              # port, serial, data
        self.port_disconnection_callback = dummy_func2     # port
        self.interrupt_callback = dummy_func_no_arg              # none
        self.loop_callback = dummy_func_no_arg                   # none

    def list_ports(self):
        """Return a list of available serial ports."""
        try:
            return [port.device for port in serial.tools.list_ports.comports()]
        except Exception as e:
            raise RuntimeError(f"Error listing ports: {e}")

    def open_port(self, port=None):
        """Open the specified serial port or raise an error."""
        if not port and not self.port:
            raise ValueError("No port specified")
        port = port or self.port
        try:
            self.serial = serial.Serial(port=port, baudrate=self.baudrate, timeout=self.timeout)
            self.port = port
            self.port_connection_found_callback(port, self.serial)
        except serial.SerialException as e:
            raise RuntimeError(f"Failed to open port {port}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error opening port {port}: {e}")

    def read_serial(self):
        """Read data from the serial port."""
        while not self.close and self.serial and self.serial.is_open:
            try:
                data = self.serial.readline().decode('utf-8').strip()
                if data:
                    self.port_read_callback(self.port, self.serial, data)
            except serial.SerialException as e:
                self.port_disconnection_callback(self.port)
                self.close_port()
                break
            except Exception as e:
                pass  # Ignore other errors, continue reading
            time.sleep(0.001)  # Prevent high CPU usage

    def send_to_port(self, data):
        """Send data to the serial port."""
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("Serial port not open")
        try:
            self.serial.write((data + '\n').encode('utf-8'))
        except serial.SerialException as e:
            raise RuntimeError(f"Error sending to {self.port}: {e}")

    def close_port(self):
        """Close the serial port."""
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except:
                pass
        self.serial = None
        self.port = None

    def Start(self):
        """Start monitoring the serial port."""
        if not self.serial or not self.serial.is_open:
            self.open_port()
        read_thread = threading.Thread(target=self.read_serial)
        read_thread.daemon = True
        read_thread.start()
        try:
            while not self.close:
                self.loop_callback()
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.interrupt_callback()
            self.Stop()

    def Stop(self):
        """Stop monitoring and close the port."""
        self.close = True
        self.close_port()