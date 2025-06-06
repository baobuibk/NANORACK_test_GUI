import os
import json
import threading
import time
import serial
import serial.tools.list_ports 
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, WindowAlign
from prompt_toolkit.widgets import Frame, TextArea
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from datetime import datetime
from prompt_toolkit.layout.containers import Window
import pytz
import re
from tabulate import tabulate
from ThreadSerial import ThreadSerial

class RaspiGUI:

    def __init__(self):
        
        self.prev_rows, self.prev_cols = os.get_terminal_size()

        self.sensor_value = [[None]*1 for _ in range(1)]
        #self.sensor_value = [[str(col).center(15) for col in row] for row in self.sensor_value]
        #self.sensor_value = [[str(col).ljust(11) for col in row] for row in self.sensor_value]
        self.output_log_line = [0,0,0,0,0,0]
        self.port_buffer = None
        self.editing_field = None
        self.formatted = []
        self.kb = KeyBindings()
        self.mode = 'menu'
        self.selected_item = 0
        self.app = Application(key_bindings=self.kb, full_screen=True)
        self.container = self.get_container()

        self.text_from_command = "NO VALUE"
        self.serial_thread = None
        self.serial_port = None
        
        if not os.path.exists("./Data"):
            os.makedirs("./Data")

        if not os.path.exists("./Log"):
            os.makedirs("./Log")

        start_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.uart_log_filename = f"./Log/Log_{start_ts}.log"
        try:
            self.uart_log_file = open(self.uart_log_filename, "a")  # 'ab' để ghi nhị phân
        except Exception as e:
            print(f"Error opening UART log file {self.uart_log_filename}: {e}")
            self.uart_log_file = None

        self.save_data_flag = False    
 
        self.log_lines = [] 
        self.max_log_lines = None 

        # Khởi tạo log_command_input
        self.log_command_input = TextArea(
            height=3,
            prompt=">>> ",
            multiline=False,
            accept_handler=self.handle_log_command
        )

        self.selected_info = 0
        self.data_input_log = 0
        self.menu_items = [
            "────────────────",
            " PreSetup  ",
            "────────────────",
            "  Config   ",
             "────────────────",
            " Tracking ",
             "────────────────",
            "  Manual   ",
             "────────────────",
            " Terminal ",
             "────────────────",
            "  Option  ",
             "────────────────",
            "   Quit    ",
            "────────────────"
        ]
        
        self.settings_data = {}
        ports = self.get_available_ports()
        default_com = ports[0] if ports else ""
        default_data = {
            "Config": [
                {"key": "CPU Usage", "value": " "},
                {"key": "Memory Usage", "value": " "},
            ],
            "Status": [
                {"key": "CPU Usage", "value": " "},
                {"key": "Memory Usage", "value": " "},
                {"key": "Disk Usage", "value": " "},
                {"key": "Temperature", "value": " "}
            ],
            "PreSetup": [
                {"key": "SSH Service", "value": "Disable"},
                {"key": "Type Connect", "value": "Serial"},
                {"key": "Port", "value": ""},
                {"key": "BaudRate", "value": 0}
            ],
            "Tracking": [
                {"key": "GPS", "value": "Active"},
                {"key": "Last Update", "value": self.get_datetime()}
            ],
            "Manual": [
                {"key": "ADC Peripheral", "value": "External"},
                # {"key": "Set Laser", "value": "No"},
                {"key": "Laser Type", "value": "Internal"},
                {"key": "Laser Index", "value": "0"},
                {"key": "Laser DAC", "value": "0"},
                # {"key": "Get Current", "value": "No"},
                {"key": "Current Type", "value": "Internal"},
                # {"key": "Get PhotoDiode", "value": "No"},
                {"key": "PhotoDiode Index", "value": "0"}
            ],
            "Terminal": [
                {"key": "Log Level", "value": "INFO"},
                {"key": "Errors", "value": "0"}
            ],
            "Option": [
                {"key": "Save file path", "value": "Vietnamese"},
                {"key": "Prefix", "value": "Dark"}
            ],
            "Quit": (
                "SpaceLiinTech\n"
                "[Project: BEE-PC1]\n"
                "[2025]\n"
            )
        }

        self.menu_list = ["PreSetup","Config","Tracking","Manual","Terminal","Option","Quit"]

        self.style = Style.from_dict({
            'window': 'bg:#333333 #ffffff',
            'frame.border': '#FFFFBB',
            'frame.label':'#FFA500',
            'sizeframe.border': '#1313c2',   
            'datetimeframe.border': '#FF00FF',  
            'statusframe.border': '#00FF00',  
            'title': 'bold #00ff00',
            'menu.item': '#ffffff',
            'menu.selected': 'reverse',
            'info.title': 'bold #00ff00',
            'info.selected': 'reverse',
            'key': '#00ff00',
            'value': '#ffffff',
            'log': '#00ff00',
            'status': '#888888',
            'raspberry.red': '#ff0000',
            'raspberry.green': '#00ff00',     
        })
        

        categories = ["Config", "Status", "PreSetup", "Tracking", "Manual", "Terminal", "Option", "Quit"]
        for cat in categories:
            filename = f"{cat}.json"
            self.settings_data[cat] = self.load_category_data(filename, default_data[cat])
            if cat == "PreSetup":
                for entry in self.settings_data[cat]:
                    if entry.get("key") == "Port":
                        if entry.get("value", "") != "":
                            entry["value"] = ""
                            changed = True
            #Hàm này để load từ các file.json vào list self.settings_data, tên các file json cũng ứng với danh mục trong categories
            #self.settings_data lưu dưới dạng các dict lồng nhau

        self.update_serial_status()

        self.utils_data = {
            "timestamp": "unknown",
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "temperature": 0
        }
        self.setup_keybindings()

        threading.Thread(target=self.update_utils_data, daemon=True).start()

        self.recommended_command = [
            ["clear: to clear the screen"],
            ["get_temp: to get the temperature of the CPU"],
            ["get_time: to get the current time"],
            # ["set_laser: to set laser | format: set_laser [int/ext] [index] [dac_value]"],
            # ["get_current: to get the current"],
            # ["pd_get: to get photodiode | format: pd_get [index]"]
        ]
        
    
        self.create_info_log =" "
        self.create_logs_log =" "

        self.status_text = "Active"
        
        self.serial_connected = False

        self.current_log = " "
        self.output_counter = 0

        #TẠO LUỒNG ĐỂ CHẠY THỜI GIAN
        time_thread = threading.Thread(target=self.load_time, daemon=True)
        time_thread.start()

        #TẠO LUỒNG UPDATE VALUE SENSOR
        sensor_thread = threading.Thread(target= self.send_to_matrix, daemon=True)
        sensor_thread.start()

    def _get_log_text(self):

        return self.current_log
    
    def write_log(self, text: str):

        self.current_log = text

    def test(self):
        self.output_counter += 1
        self.current_log = f">>>: Output ({self.output_counter}) <<<"

    def clear_log(self):

        self.current_log = ""

    def get_available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def set_status_text(self, text):
        """
        Cập nhật nội dung ô status và invalidate để vẽ lại ngay lập tức.
        """
        self.status_text = text
        # Nếu ứng dụng đã chạy (self.app đã được tạo), hãy gọi invalidate() để cập nhật UI.
        try:
            self.app.invalidate()
        except Exception:
            pass

    def close_branch_datalog(self):
        # 1. Nếu đang ở chế độ “Open”, thì đóng file Data và tắt flag
        if self.save_data_flag:
            self.save_data_flag = False
            if self.data_log_file:
                try:
                    self.data_log_file.close()
                    self.write_log(">>>: Data file closed (auto)")
                except Exception as e:
                    self.write_log(f">>>: Error closing Data file: {e}")
                finally:
                    self.data_log_file = None

            # 2. Nếu đang xem menu Manual và focus đúng Step 2, 
            #    thì đặt lại giá trị của field về "Open"
            selectable_items = self.get_selectable_items()
            if self.mode == 'info' and selectable_items[self.selected_item] == "Manual":
                manual_list = self.settings_data["Manual"]
                if 0 <= self.selected_info < len(manual_list):
                    current_field = manual_list[self.selected_info]
                    if current_field["key"] == "Step 2: ->[Send - PhotoDiode Get]":
                        current_field["value"] = "Close"


    def update_serial_status(self):
        for cat in ["PreSetup", "Manual"]:
            for item in self.settings_data[cat]:
                if item["key"] == "Serial Port":
                    item["value"] = "Enable" if self.serial_port and self.serial_port.is_open else "Disable"
                    break

    #TAO 1 LUONG DE LIEN TUC UPDATE THOI GIAN 
    def load_time(self):
        while True:
            self.utils_data["timestamp"]=datetime.now().strftime("%d/%m/%Y,%H:%M:%S")
            with open("time.txt","w") as file:
                file.write(datetime.now().strftime("%d/%m/%Y,%H:%M:%S"))
            time.sleep(1)
    



    def load_category_data(self, filename, default_data):
        if not os.path.exists(filename):
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Error writing {filename}: {e}")
            return default_data
        else:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                return default_data


    def is_divider(self, item):
        return set(item.strip()) == {"─"}

    def get_terminal_size(self):
        return f"{os.get_terminal_size().columns}x{os.get_terminal_size().lines}"

    def get_datetime(self):
        now = datetime.now(pytz.UTC)
        return now.strftime("%Y-%m-%d %H:%M:%S GMT")

    def get_latest_log(self):
        try:
            with open("notice.log", "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if lines:
                    return lines[-1]
                else:
                    return "No logs available"
        except Exception as e:
            return f"Error reading log: {e}"

    def update_utils_data(self):
        while True:
            try:
                with open("utils.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.utils_data = data
            except Exception:
                pass
            time.sleep(1)

    def get_status_text(self):
        try:
            cpu = f"{float(self.utils_data.get('cpu_usage', 0)):.1f}%"
        except Exception:
            cpu = "-"
        try:
            mem = f"{float(self.utils_data.get('memory_usage', 0)):.1f}%"
        except Exception:
            mem = "-"
        try:
            disk = f"{float(self.utils_data.get('disk_usage', 0)):.1f}%"
        except Exception:
            disk = "-"
        try:
            temp = f"{float(self.utils_data.get('temperature', 0)):.1f}°C"
        except Exception:
            temp = "-"
        return f"CPU: {cpu}\nMem: {mem}\nDisk: {disk}\nTemp: {temp}"

    def create_header(self):
        size_frame = Frame(
            Window(FormattedTextControl(lambda: f"{os.get_terminal_size().columns}x{os.get_terminal_size().lines}"),
                   align=WindowAlign.CENTER),
            width=12,
            height=3,
            title='Size'
        )
        datetime_frame = Frame(
            Window(FormattedTextControl(lambda: f"[OBC-GUI] DateTime: {self.utils_data.get('timestamp', 'unknown')}"), align=WindowAlign.CENTER),

            width=None,
            height=3,
            title='Datetime'
        )
        status_frame = Frame(
            Window(
                FormattedTextControl(lambda: self.status_text),
                align=WindowAlign.CENTER
            ),
            width=14,
            height=3,
            title="Status"  # (tuỳ chọn) nếu bạn muốn ghi tiêu đề cho khung này
        )

        return VSplit([size_frame, datetime_frame, status_frame])


    def setup_keybindings(self):

        #viết một hàm với sự kiện là nó sẽ thực hiện nếu ta bấm phím mũi tên lênlên
        @self.kb.add('up')
        def _(event):
            if self.mode == 'menu':
                selectable_count = sum(1 for item in self.menu_items if not self.is_divider(item))
                self.selected_item = max(0, self.selected_item - 1)
                self.lasted_selected_item = self.selected_item
                selectable_items = self.get_selectable_items()
                self.info_frame.title = selectable_items[self.selected_item]
                
            elif self.mode == 'info':
                self.close_branch_datalog()
                selectable_items = self.get_selectable_items()
                if selectable_items[self.selected_item] in ["PreSetup", "Manual", "Config"]:
                    if self.selected_info > 0:
                        self.selected_info -= 1
                        self.port_buffer = None
                        self.editing_field = None
            self.container = self.get_container()
            self.layout.container = self.container
            event.app.invalidate()

        @self.kb.add('down')
        def _(event):
            if self.mode == 'menu':
                selectable_count = sum(1 for item in self.menu_items if not self.is_divider(item))
                self.selected_item = min(selectable_count - 1, self.selected_item + 1)
                self.lasted_selected_item = self.selected_item
                selectable_items = self.get_selectable_items()
                self.info_frame.title = selectable_items[self.selected_item]
            elif self.mode == 'info':
                self.close_branch_datalog()
                selectable_items = self.get_selectable_items()
                if selectable_items[self.selected_item] in ["PreSetup", "Manual", "Config"]:
                    max_info = len(self.settings_data[selectable_items[self.selected_item]])  # "Apply" index = len(data)
                    self.selected_info = min(max_info, self.selected_info + 1)
                    self.port_buffer = None
                    self.editing_field = None
            self.container = self.get_container()
            self.layout.container = self.container
            event.app.invalidate()
            

        @self.kb.add('enter')
        def _(event):
            # self.test()
            
            if event.app.layout.has_focus(self.log_command_input):
                buf = self.log_command_input.buffer
                if buf.validate():  # Kiểm tra dữ liệu hợp lệ trước khi gửi
                    buf.accept_handler(buf)  # Gọi hàm xử lý khi nhấn Enter

            if self.mode == 'menu':
                selectable_items = self.get_selectable_items()
                if selectable_items[self.selected_item] == "Quit":
                    event.app.exit()
                else:
                    self.mode = 'info'
                    self.selected_info = 0
                    self.port_buffer = None
                    self.editing_field = None
                    if selectable_items[self.selected_item] == "Logs":  # Focus vào TextArea
                        if hasattr(self, 'log_command_input'):
                            event.app.layout.focus(self.log_command_input)
                    else:
                        event.app.layout.focus(self.info_window)
                    self.lasted_selected_item = self.selected_item
            elif self.mode == 'info':
                selectable_items = self.get_selectable_items()
                selected_key = selectable_items[self.selected_item]
                if selected_key in ["PreSetup", "Manual", "Config"]:
                    data = self.settings_data[selected_key]
                    self.write_log(">>>: Type Enter")


                    if self.selected_info == len(data):

                        if selected_key == "Config":

                            if not self.serial_connected or not self.serial_thread:
                                self.write_log(">>>: Error: Communication not established")
                                return

                            config_data = self.settings_data.get("Config", [])
                            apply_index = len(config_data)
                            
                            if self.selected_info == apply_index:

                                self.write_log(">>>: I'm sending config")
                                sample_set = None
                                sample_rate = None
                                for item in data:
                                    if item["key"] == "SampleSet[Sample]":
                                        sample_set = item["value"]
                                    if item["key"] == "SampleRate[Sample/s]":
                                        sample_rate = item["value"]
                                if sample_set.isdigit() and sample_rate.isdigit():
                                    try:
                                        self.serial_thread.send_to_port(f"sp_set_rate {sample_rate} {sample_set}")
                                        self.write_log("Sent: OK")
                                    except RuntimeError as e:
                                        self.write_log(f"Sent: Fail - {e}")


                                try:
                                    with open("Config.json", "w", encoding="utf-8") as f:
                                        json.dump(config_data, f, indent=4, ensure_ascii=False)
                                    self.create_info_log = "Config OK!"
                                except Exception as e:
                                    self.create_info_log = f"Error save: {e}"
                                # Quay về menu hoặc bạn có thể giữ ở info và reset selected_info=0
                                self.mode = 'menu'
                                event.app.layout.focus(self.menu_window)




                    if self.selected_info < len(data):
                        current_field = data[self.selected_info]

                        if selected_key == "Config":
                            config_data = self.settings_data.get("Config", [])
                            apply_index = len(config_data)
                            
                            if self.selected_info == apply_index:

                                try:
                                    with open("Config.json", "w", encoding="utf-8") as f:
                                        json.dump(config_data, f, indent=4, ensure_ascii=False)
                                    self.create_info_log = "Config saved!"
                                except Exception as e:
                                    self.create_info_log = f"Error save: {e}"
                                # Quay về menu hoặc bạn có thể giữ ở info và reset selected_info=0
                                self.mode = 'menu'
                                event.app.layout.focus(self.menu_window)

                        elif selected_key == "PreSetup":
                            if current_field["key"] in ["Type Connect"]:
                                pass
                                # current_field["value"] = "Serial" if current_field["value"] == "TCP/IP" else "TCP/IP"
                            # if current_field["key"] in ["SSH Service"]:
                            #     current_field["value"] = "Disable" if current_field["value"] == "Enable" else "Enable"

                            elif current_field["key"] == "Port":
                                ports = self.get_available_ports()
                                if not ports:
                                    self.create_info_log = "No available Port"
                                else:
                                    current_value = current_field["value"]
                                    if current_value in ports:
                                        current_index = ports.index(current_value)
                                        next_index = (current_index + 1) % len(ports)
                                        current_field["value"] = ports[next_index]
                                    else:
                                        current_field["value"] = ports[0]
                                self.container = self.get_container()
                                self.layout.container = self.container
                                event.app.invalidate()
                                return        
                        elif selected_key == "Manual":
                            if current_field["key"] == "$: >[Send - Laser Set]":
                                if not self.serial_connected or not self.serial_thread:
                                    self.write_log(">>>: Error: Communication not established")
                                    return
                                self.write_log(">>>: I'm sending laser")
                                laser_type = None
                                laser_index = None
                                for item in data:
                                    if item["key"] == "Laser Type":
                                        laser_type = item["value"]
                                    if item["key"] == "Laser Index":
                                        laser_index = item["value"]
                                    if item["key"] == "Laser DAC":
                                        dac_voltage = item["value"]
                                if laser_type in ["Internal", "External"] and laser_index.isdigit() and dac_voltage.isdigit():
                                    try:
                                        cmd_laser_type = 'int' if laser_type == 'Internal' else 'ext'
                                        self.serial_thread.send_to_port(f"set_laser {cmd_laser_type} {laser_index} {dac_voltage}")
                                        self.write_log("Sent: OK")
                                    except RuntimeError as e:
                                        self.write_log(f"Sent: Fail - {e}")


                            elif current_field["key"] == "$: >[Send - Current Get]":
                                if not self.serial_connected or not self.serial_thread:
                                    self.write_log(">>>: Error: Communication not established")
                                    return
                                self.write_log(">>>: I'm sending current")
                                current_type = None
                                for item in data:
                                    if item["key"] == "Current Type":
                                        current_type = item["value"]

                                if current_type in ["Internal", "External"]:
                                        try:
                                            cmd_current_type = 'int' if current_type == 'Internal' else 'ext'
                                            self.serial_thread.send_to_port(f"get_current {cmd_current_type}")
                                            self.write_log("Sent: OK")
                                        except RuntimeError as e:
                                            self.write_log(f"Sent: Fail - {e}")



                            elif current_field["key"] == "Step 2: ->[Send - PhotoDiode Get]":
                                if not self.serial_connected or not self.serial_thread:
                                    self.write_log(">>>: Error: Communication not established")
                                    return                                
                                current_field["value"] = "Close" if current_field["value"] == "Open" else "Open"
                                if current_field["value"] == "Open":
                                    try:
                                        photodiode_index = None
                                        for item in data:  # data = self.settings_data["Manual"]
                                            if item["key"] == "PhotoDiode Index":
                                                photodiode_index = item["value"]
                                                break
                                        if photodiode_index is None:
                                            photodiode_index = "0"

                                        self.save_data_flag = True
                                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        data_filename = f"./Data/Index{photodiode_index}_{ts}.log"
                                        try:
                                            self.data_log_file = open(data_filename, "a")  # 'ab' để ghi bytes
                                        except Exception as e:
                                            self.write_log(f"Error opening Data file: {e}")
                                            self.data_log_file = None

                                        self.serial_thread.send_to_port(f"sp_get_buf_c")
                                        self.write_log("Sent: OK")
                                    except RuntimeError as e:
                                        self.write_log(f"Sent: Fail - {e}")
                                else:
                                        self.save_data_flag = False

                                        if self.data_log_file:
                                            try:
                                                self.data_log_file.close()
                                                self.write_log(f">>>: Data file closed")
                                            except Exception as e:
                                                self.write_log(f">>>: Error closing Data file: {e}")
                                            finally:
                                                self.data_log_file = None

                            elif current_field["key"] == "Step 1: ->[Send - Trigger Read]":
                                if not self.serial_connected or not self.serial_thread:
                                    self.write_log(">>>: Error: Communication not established")
                                    return                                

                                try:
                                    self.serial_thread.send_to_port(f"sp_trig")
                                    self.write_log("Sent: OK")
                                except RuntimeError as e:
                                    self.write_log(f"Sent: Fail - {e}")


                            elif current_field["key"] == "Step 0: ->[Send - PhotoDiode Set]":
                                if not self.serial_connected or not self.serial_thread:
                                    self.write_log(">>>: Error: Communication not established")
                                    return                                
                                photodiode_index = None
                                for item in data:
                                    if item["key"] == "PhotoDiode Index":
                                        photodiode_index = item["value"]

                                if photodiode_index.isdigit():
                                        try:
                                            self.serial_thread.send_to_port(f"sp_set_pd {photodiode_index}")
                                            self.write_log("Sent: OK")
                                        except RuntimeError as e:
                                            self.write_log(f"Sent: Fail - {e}")



                            # if current_field["key"] in ["Set Laser", "Get Current", "Get PhotoDiode"]:
                            #     current_field["value"] = "No" if current_field["value"] == "Yes" else "Yes"
                            if current_field["key"] in ["ADC Peripheral", "Laser Type", "Current Type"]:
                                current_field["value"] = "External" if current_field["value"] == "Internal" else "Internal"
                    else:
                        filename = f"{selected_key}.json"

                        try:
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=4, ensure_ascii=False)
                            if selected_key == "PreSetup":
                                # self.test()

                                serial_enabled = False
                                com_port = None
                                baudrate = None
                                for item in data:
                                    if item["key"] == "Type Connect" and item["value"] == "Serial":
                                        serial_enabled = True
                                    if item["key"] == "Port":
                                        com_port = item["value"]
                                    if item["key"] == "BaudRate":
                                    # Lấy giá trị từ JSON, có thể là số hoặc chuỗi số
                                        try:
                                            baudrate = int(item["value"])
                                        except Exception:
                                            baudrate = None


                                if serial_enabled and com_port:
                                    try:

                                        if self.serial_thread:
                                            self.serial_thread.Stop()
                                            self.serial_thread = None
                                            self.serial_connected = False

                                        self.serial_thread = ThreadSerial( port=com_port, baudrate=baudrate, timeout= 1)
                                        self.serial_thread.port_connection_found_callback = self.on_serial_connect
                                        self.serial_thread.port_read_callback = self.on_serial_data
                                        self.serial_thread.port_disconnection_callback = self.on_serial_disconnect
                                        threading.Thread(target=self.serial_thread.Start, daemon=True).start()
                                        self.write_log(f">>>: {com_port} Opened, Baudrate: {baudrate}")
                                    except RuntimeError as e:
                                        self.write_log(f">>>: Failed to open port {com_port}: {e}")
                                        self.serial_connected = False
                                else:
                                    if self.serial_thread:
                                        self.serial_thread.Stop()
                                        self.serial_thread = None
                                        self.write_log(">>>: Port closed")
                                    elif serial_enabled:
                                        self.write_log(">>>: Invalid Port")
                                self.update_serial_status()
                            elif selected_key == "Manual":
                                pass
                        except Exception as e:
                            pass
                        self.mode = 'menu'
                        event.app.layout.focus(self.menu_window)
            self.container = self.get_container()
            self.layout.container = self.container            
            event.app.invalidate()

        @self.kb.add('escape')
        def _(event):
            self.write_log(">>>: Exit")
            self.close_branch_datalog()
            if self.mode == 'info':
                self.mode = 'menu'
                self.selected_info = 0
                self.port_buffer = None
                self.editing_field = None
                event.app.layout.focus(self.menu_window)
                self.lasted_selected_item = self.selected_item
            self.container = self.get_container()
            self.layout.container = self.container
            event.app.invalidate()

        @self.kb.add('c-c')
        def _(event):
            event.app.exit()

        for digit in "0123456789": 
            @self.kb.add(digit) 
            def _(event, digit=digit): 

                if (hasattr(self, 'log_command_input') 
                    and event.app.layout.has_focus(self.log_command_input)):
                    buffer = self.log_command_input.buffer
                    buffer.insert_text(digit)
                    return
                
                if self.mode == 'info':
                    selectable_items = self.get_selectable_items()  #tạo 1 bảng selectable_items với các phần tử không có dấu "-"
                    current_field = None
                    # if selectable_items[self.selected_item] == "PreSetup":
                    #     current_field = self.settings_data["PreSetup"][self.selected_info] #current_field sẽ lưu 1 thành phần dict của PreSetup
                    #     if current_field["key"] in ["Port", "Photodiode Get"]:
                    #         if self.port_buffer is None or self.port_buffer == "0":
                    #             self.port_buffer = digit
                    #         else:
                    #             self.port_buffer += digit
                    #         current_field["value"] = self.port_buffer

                    if selectable_items[self.selected_item] == "PreSetup":
                        current_index = self.selected_info
                        presetup_data = self.settings_data["PreSetup"]

                        # Trường Port (index = 2) thì vẫn dùng nút Enter để cycle qua các cổng
                        # Còn trường BaudRate (index = 3) cho phép nhập số
                        if current_index == 3:  
                            # Lấy buffer hiện tại, thêm chữ số mới
                            new_buf = (self.port_buffer or "") + digit
                            # Giới hạn giá trị BaudRate tối đa (ví dụ <= 1000000)
                            if int(new_buf) <= 100000000:
                                self.port_buffer = new_buf.lstrip("0") or "0"
                                # Lưu tạm vào data (value hiển thị luôn)
                                presetup_data[current_index]["value"] = self.port_buffer
                        # Nếu không phải mục BaudRate, không làm gì ở đây

                        # Cập nhật lại giao diện
                        self.container = self.get_container()
                        self.layout.container = self.container
                        event.app.invalidate()


                    if selectable_items[self.selected_item] == "Config":
                        current_index = self.selected_info
                        config_data = self.settings_data["Config"]
                        if current_index in [0, 1]:
                            # bám sát logic giống Manual:
                            new_buf = (self.port_buffer or "") + digit
                            if current_index == 0:  # Sample to get, giới hạn ví dụ <= 75000
                                if int(new_buf) <= 75000:
                                    self.port_buffer = new_buf.lstrip("0") or "0"
                                    config_data[current_index]["value"] = self.port_buffer
                            elif current_index == 1:  # Sample rate
                                # Giới hạn tùy ý, hoặc không giới hạn
                                self.port_buffer = new_buf.lstrip("0") or "0"
                                config_data[current_index]["value"] = self.port_buffer
                            self.container = self.get_container()
                            self.layout.container = self.container
                            event.app.invalidate()

                    if selectable_items[self.selected_item] == "Manual":
                        current_field = self.settings_data["Manual"][self.selected_info]
                        if current_field["key"] in ["Laser Index", "Laser DAC", "PhotoDiode Index"]:
                            new_buffer = (self.port_buffer or "0") + digit
                            if current_field["key"] in ["Laser Index", "PhotoDiode Index"]:
                                if int(new_buffer) <= 36:
                                    self.port_buffer = new_buffer.lstrip("0") or "0"
                                    current_field["value"] = self.port_buffer
                            elif current_field["key"] == "Laser DAC":
                                if int(new_buffer) <= 100:
                                    self.port_buffer = new_buffer.lstrip("0") or "0"
                                    current_field["value"] = self.port_buffer
                    if current_field:
                        self.lasted_selected_item = self.selected_item
                        event.app.invalidate()

       
        

        @self.kb.add('backspace')
        def _(event):
            if event.app.layout.has_focus(self.log_command_input):
                buf = self.log_command_input.buffer
                if buf.cursor_position > 0:
                    buf.delete_before_cursor(count=1)

            if self.mode == 'info':
                selectable_items = self.get_selectable_items()

            # Xử lý Backspace cho PreSetup
            if selectable_items[self.selected_item] == "PreSetup":
                current_index = self.selected_info
                presetup_data = self.settings_data["PreSetup"]
                if current_index == 3 and self.port_buffer:  # chỉ xóa khi focus BaudRate
                    # Xóa ký tự cuối
                    self.port_buffer = self.port_buffer[:-1]
                    # Cập nhật lại vào data
                    if self.port_buffer:
                        presetup_data[current_index]["value"] = self.port_buffer
                    else:
                        # Nếu xóa hết, để về "0" hoặc "" tùy bạn muốn
                        self.port_buffer = ""
                        presetup_data[current_index]["value"] = ""

                    # Refresh UI
                    self.container = self.get_container()
                    self.layout.container = self.container
                    event.app.invalidate()
                    return  # thoát, không cần xuống tiếp


            if self.mode == 'info':
                selectable_items = self.get_selectable_items()
                current_field = None
                if selectable_items[self.selected_item] == "Config":
                    current_index = self.selected_info
                    config_data = self.settings_data["Config"]
                    if current_index in [0, 1] and self.port_buffer:
                        self.port_buffer = self.port_buffer[:-1]
                        if self.port_buffer:
                            config_data[current_index]["value"] = self.port_buffer
                        else:
                            config_data[current_index]["value"] = "0"
                        self.container = self.get_container()
                        self.layout.container = self.container
                        event.app.invalidate()
                # if selectable_items[self.selected_item] == "PreSetup":
                #     current_field = self.settings_data["PreSetup"][self.selected_info]
                #     if current_field["key"] in ["Port", "Photodiode Get"]:
                #         if self.port_buffer is not None and len(self.port_buffer) > 0:
                #             self.port_buffer = self.port_buffer[:-1]
                #             current_field["value"] = self.port_buffer if self.port_buffer else "0"
                if selectable_items[self.selected_item] == "Manual":
                    current_field = self.settings_data["Manual"][self.selected_info]
                    if current_field["key"] in ["Laser Index", "Laser DAC", "PhotoDiode Index"]:
                        if self.port_buffer is not None and len(self.port_buffer) > 0:
                            self.port_buffer = self.port_buffer[:-1]
                            current_field["value"] = self.port_buffer if self.port_buffer else "0"
                if current_field:
                    self.lasted_selected_item = self.selected_item
                    event.app.invalidate()


    def on_serial_connect(self, port, ser):
        self.write_log(f">>>: {port} Opened, Baudrate: {ser.baudrate}")
        self.serial_connected = True
        self.set_status_text("Connected")

    def on_serial_data(self, port, ser, data):

        self.write_log(f">>>: Received from {port}: (Length: {len(data)})")
        try:
            text = data.decode('utf-8', errors='ignore') + '\n' if isinstance(data, (bytes, bytearray)) else str(data) + '\n'
            text_backup = data.decode('utf-8', errors='ignore') if isinstance(data, (bytes, bytearray)) else str(data)
        except:
            text = str(data) + '\n'
            text_backup = str(data)

        if self.save_data_flag:
            if self.data_log_file:
                try:
                    self.data_log_file.write(text)
                    self.data_log_file.flush()
                except Exception:
                    pass
        else:
            if self.uart_log_file:
                try:
                    self.uart_log_file.write(text)
                    self.uart_log_file.flush()
                except Exception:
                    pass

        if not self.save_data_flag:
            new_entry = f"⇒ {text_backup}"
            self.log_lines.append(new_entry)

            if self.max_log_lines is None:
                rows, cols = os.get_terminal_size()
                self.max_log_lines = max(1, int(rows // 6.7))
            if len(self.log_lines) > self.max_log_lines:
                self.log_lines.pop(0)

            try:
                self.app.invalidate()
            except Exception:
                pass


    # def on_serial_data(self, port, ser, data):

    #     self.write_log(f">>>: Received from {port}: (Length: {len(data)})")
    #     try:
    #         text = data.decode('utf-8', errors='ignore') if isinstance(data, (bytes, bytearray)) else str(data)
    #     except:
    #         text = str(data)

    #     new_entry = f"⇒ {text}"

    #     # Append và giữ độ dài tối đa
    #     self.log_lines.append(new_entry)

    #     if self.max_log_lines is None:
    #         rows, cols = os.get_terminal_size()
    #         self.max_log_lines = rows//6.7
    #         if self.max_log_lines < 1:
    #             self.max_log_lines = 1
    #     if len(self.log_lines) > self.max_log_lines:
    #         self.log_lines.pop(0)

    #     try:
    #         self.app.invalidate()
    #     except Exception:
    #         pass

    def on_serial_disconnect(self, port):
        self.write_log(f">>>: Disconnected from {port}")

    def create_menu_content(self):  
        content = []         
        selectable_index = 0  

        for item in self.menu_items:
            if self.is_divider(item): 
                content.append(('', item + "\n"))  
            else:
                style = 'class:menu.selected' if selectable_index == self.selected_item else 'bold' #nếu cái index của hàm này bằng với cái self.selected_item, nghĩa là ta đang chọn mục đó thì nó sẽ lưu tuple(với style là class..., nội dung), còn không thì nó chỉ có style là bold
                content.append((style, f"{item}\n"))
                selectable_index += 1
        return content

        
    def get_selectable_items(self):
        return [item.strip() for item in self.menu_items if not self.is_divider(item)]


    def create_info_content(self):
        selectable_items = self.get_selectable_items()     
        selected_key = selectable_items[self.selected_item]  
        if selected_key == "Quit":
            logo = self.settings_data.get("Quit", "\n  No information available")
            term_size = os.get_terminal_size()
            term_width = term_size.columns-28
            fixed_info_height = 0  # chiều cao cố định của vùng info
            logo_lines = logo.splitlines()
            num_logo_lines = len(logo_lines)
            pad_top = 0
            centered_lines = []
            for _ in range(pad_top):
                centered_lines.append(('', '\n'))
            for line in logo_lines:
                centered_lines.append(('class:info', line.center(term_width)))
                centered_lines.append(('', '\n'))
            return centered_lines
        
        elif selected_key in ["PreSetup", "Manual"]: 
            content = [] 
            if selected_key == "PreSetup":
                content.append(('class:frame.label', f"\n  ---> {selected_key}: \n\n"))
            elif selected_key == "Manual":
                pass

            data = self.settings_data[selected_key]
            for i, item in enumerate(data): 
                display_value = f"{item['value']}"
                if selected_key == "PreSetup" and item["key"] == "COM" and display_value:
                    display_value = f"{display_value}"  
                if selected_key == "Manual" and i == 0:
                    term_size = os.get_terminal_size()
                    term_width = term_size.columns - 28
                    separator = "---[Laser]"+"-" * term_width + "\n"
                    content.append(('class:info', separator))
                
                if self.selected_info == i and self.mode == 'info':
                    key_style = 'class:info.selected'   
                    value_style = 'class:info.selected'  
                else:
                    if item["key"] == "$: >[Send - Laser Set]" or item["key"] == "$: >[Send - Current Get]":  
                        key_style = 'class:frame.label'
                        value_style = 'class:value'
                    elif item["key"] == "Step 0: ->[Send - PhotoDiode Set]" or item["key"] == "Step 1: ->[Send - Trigger Read]" or item["key"] == "Step 2: ->[Send - PhotoDiode Get]":
                        key_style = 'class:frame.label'
                        value_style = 'class:value'
                    else:
                        key_style = 'class:key'
                        value_style = 'class:value'
                content.append((key_style, f"  {item['key']}: "))
                content.append((value_style, f"{item['value']}\n"))
                if selected_key == "Manual":

                    term_size = os.get_terminal_size()
                    term_width = term_size.columns - 28
                    separator = "-" * term_width + "\n"

                    if item["key"] == "$: >[Send - Laser Set]":
                        separator = "---[Laser Current]"+"-" * term_width + "\n"
                        content.append(('class:info', separator))

                    if item["key"] == "Laser DAC" or item["key"] == "Current Type" or item["key"] == "PhotoDiode Index":
                        pass
                        # separator = "-" * term_width + "\n"
                        # content.append(('class:info', separator))
  
                    elif item["key"] == "$: >[Send - Current Get]":
                        # content.append(('class:info', separator))
                        separator = "---[PhotoDiode]"+"-" * term_width + "\n"
                        content.append(('class:info', separator))


            if selected_key == "PreSetup":
                if self.selected_info == len(data) and self.mode == 'info':
                    apply_style = 'class:info.selected'
                else:
                    apply_style = 'class:info'
                term_size = os.get_terminal_size()
                term_width = term_size.columns-28
                apply_text = "[ Connect ]".center(term_width)
                content.append((apply_style, apply_text+"\n"))


            # if self.selected_info == len(data) and self.mode == 'info':
            #     apply_style = 'class:info.selected'
            # else:
            #     apply_style = 'class:info'
            # term_size = os.get_terminal_size()
            # term_width = term_size.columns-28
            # if selected_key == "PreSetup":
            #     apply_text = "[ Connect ]".center(term_width)
            # elif selected_key == "Manual":
            #     apply_text = "[ Send ]".center(term_width)
            # content.append((apply_style, apply_text+"\n"))
            return content #nó sẽ trả về 1 list chứa các tuple, mỗi tuple sẽ là style của text với text là key hoặc value
            

        elif selected_key == "Tracking":
            content = self.formatted 
            return content

        elif selected_key == "Config":
            content = []
            content.append(('class:frame.label', f"\n  ---> Config:\n\n"))
            config_data = self.settings_data.get("Config", [])
            term_size = os.get_terminal_size()
            term_width = term_size.columns - 28


            for i, field in enumerate(config_data):
                if self.selected_info == i and self.mode == 'info':
                    key_style = 'class:info.selected'
                    value_style = 'class:info.selected'
                else:
                    key_style = 'class:key'
                    value_style = 'class:value'

                content.append((key_style, f"  {field['key']}: "))
                content.append((value_style, f"{field['value']}\n"))

            apply_index = len(config_data)
            if self.selected_info == apply_index and self.mode == 'info':
                apply_style = 'class:info.selected'
            else:
                apply_style = 'class:info'
            apply_text = "[ Apply ]".center(term_width)
            content.append((apply_style, apply_text + "\n"))

            separator = "-" * term_width + "\n"
            content.append(('class:info', separator))
            content.append(('class:frame.label', f"\n  ---> Status:\n\n"))

            status_data = self.settings_data.get("Status", [])

            term_size = os.get_terminal_size()
            term_width = term_size.columns - 28

            for i, field in enumerate(status_data):
                key_style = 'class:key'
                value_style = 'class:value'
                content.append((key_style, f"  {field['key']}: "))
                content.append((value_style, f"{field['value']}\n"))


            return content       

        elif selected_key in self.settings_data:
            content = []
            content.append(('class:frame.label', f"\n  ---> {selected_key}:\n\n"))
            data = self.settings_data[selected_key]
            for item in data:
                content.append(('class:key', f"  {item['key']}: "))
                content.append(('class:value', f"{item['value']}\n"))
            return content

        else:
            return [('class:info', "\n  No information available")]
        
    
    def DAC_avarage (self):
        a = 0
        sum = 0
        for i,value in enumerate(self.output_log_line):
            if (i > 1) and (value != 0):
                sum += value*3.3/16383
                a+=1
            continue
        return f"{sum/a:.2f}" 
    

    def process_data(self,log_line):                
        patern = r"C(\d+)-(\d+)"\
                r".*?\[T: 0\]-\[ADC: (\d+)\]"\
                r"(?:.*?\[T: 1\]-\[ADC: (\d+)\])?"\
                r"(?:.*?\[T: 2\]-\[ADC: (\d+)\])?"\
                r"(?:.*?\[T: 3\]-\[ADC: (\d+)\])?"
        match = re.search(patern, log_line)

        if match:
            self.output_log_line = list(match.groups())
            self.output_log_line = [0 if x is None else x for x in self.output_log_line]
            self.output_log_line = list(map(int,self.output_log_line))
            self.sensor_value[self.output_log_line[0]-1][self.output_log_line[1]-1] = self.DAC_avarage()
            #return self.sensor_value
            self.format_table(self.output_log_line[0],self.output_log_line[1])
        
        else:
            print("No sensor data found!")

    def send_to_matrix(self):
        self.format_table(0,0)
        pass
        # with open("test.log", "r", encoding="utf-8") as file:
        #     for log_line in file:
        #         if "ADC" in log_line: #kiểm tra trong dòng log đó có kí tự nào là ADC k, nếu có thì cho phép đọc dòng đó vì đó là dòng có giá trị cảm biến
        #             self.process_data(log_line)
        #             time.sleep(1)
                    #app.invalidate()

    def format_table(self,x,y):
        self.formatted = []
        #self.sensor_value = [[str(col).ljust(15) for col in row] for row in self.sensor_value]
        table_str = tabulate(self.sensor_value,tablefmt="grid",floatfmt=".2f").split("\n")
        semaphore = 0
        row_indx, col_indx = 0,0
        for i,row in enumerate(table_str):
            if i % 2 == 0:
                for char in row:
                    self.formatted.append(("fg:white",char))
                self.formatted.append(("fg:white","\n"))
            if i % 2 != 0:
                col_indx = 0
                semaphore = 0
                for char in row:
                    if char.isdigit() or char == "." or char == " ":
                        if row_indx == (x-1) and col_indx == (y-1):
                            self.formatted.append(("bg:yellow",char))
                        else:
                            self.formatted.append(("fg:green",char))              
                    if char == "|":
                        self.formatted.append(("fg:white",char))
                        semaphore +=1
                        if semaphore > 1:
                            col_indx +=1
                    # else:
                    #     self.formatted.append(("fg:white",char))
                self.formatted.append(("fg:white","\n"))
                row_indx +=1
        return self.formatted


    #HÀM NÀY DÙNG ĐỂ XỬ LÝ LỆNH NHẬN TỪ COMMAND LINE, HOẠT ĐỘNG DỰA TRÊN VIỆC LẤY BUFFER TỪ WINDOW
    # def handle_log_command(self, buffer):
    #     self.text_from_command = buffer.text.strip()
    #     if self.text_from_command:
    #         try:
    #             # Ví dụ các lệnh xử lý
    #             if self.text_from_command.lower() == "help":
    #                 if not hasattr(self, 'create_info_log_raw'):
    #                     #self.create_info_log = None
    #                     self.create_info_log_raw = []
    #                     for data in self.recommended_command:
    #                         self.create_info_log_raw.append("".join(data)+"\n")
    #                 self.create_logs_log = "".join(self.create_info_log_raw)
    #             if self.text_from_command.lower() == "clear":
    #                 self.create_logs_log = None

                
    #         except Exception as e:
    #             self.log_command_input.text = f"Error: {str(e)}"

    #     return True  # Giữ TextArea hoạt động
    def handle_log_command(self, buffer):

        cmd = buffer.text.strip()
        buffer.text = "" 

        if cmd:
            if self.serial_connected and self.serial_thread:
                data_bytes = cmd.encode('utf-8') + b"\r\n"
                try:
                    self.serial_thread.send_to_port(cmd)
                    new_entry = f"⇐ {cmd}"
                except Exception as e:
                    new_entry = f"⇐ Error sending: {e}"

                if self.uart_log_file:
                    try:
                        self.uart_log_file.write(data_bytes)
                        self.uart_log_file.flush()
                    except Exception:
                        pass

            else:
                new_entry = "Error: Not connected"

            self.log_lines.append(new_entry)

            if self.max_log_lines is None:
                rows, cols = os.get_terminal_size()

                self.max_log_lines = (rows)//6.7# -2 vì Frame("Terminal") chiếm 2 dòng border

                if self.max_log_lines < 1:
                    self.max_log_lines = 1
            if len(self.log_lines) > self.max_log_lines:
                self.log_lines.pop(0)

        try:
            self.app.invalidate()
        except Exception:
            pass

        return True
    
    def get_container(self):

        rows, cols = os.get_terminal_size()
        if (rows, cols) != (self.prev_rows, self.prev_cols):
            self.log_lines.clear()        # hoặc self.current_log = ""
            self.max_log_lines = None
            self.prev_rows, self.prev_cols = rows, cols


        header = self.create_header()
        self.menu_window = Window(FormattedTextControl(self.create_menu_content), width=10)
        # side_window = Window(FormattedTextControl("Additional"), width=12)
        side_window = Window(
            FormattedTextControl(
                lambda: "" if self.selected_item == 4 else self.create_info_log
            ),
            width=12,
            wrap_lines=True
        )
        
        rows, cols = os.get_terminal_size()
        self.max_log_lines = (rows)//6.7# -2 vì Frame("Terminal") chiếm 2 dòng border


        side_top_window = Window(
            FormattedTextControl(lambda:
                (self.create_info_log or "")
            ),
            wrap_lines=True
        )

        side_bottom_window = Window(
            FormattedTextControl(lambda:

                (self.create_info_log or "")
            ),
            wrap_lines=True
        )

        side_top_frame = Frame(
            side_top_window,
            title="Send",
            width=14, 
            style='class:frame'
        )
        side_bottom_frame = Frame(
            side_bottom_window,
            title="Recv",
            width=14, 
            style='class:frame'
        )

        side_container = HSplit([
            side_top_frame,
            side_bottom_frame
        ])

        if self.selected_item == 4:
            self.info_up_window = Window(
                FormattedTextControl(lambda: "\n".join(self.log_lines)),
                wrap_lines=True
            )
            # Kiểm tra nếu `log_command_input` đã tồn tại, xóa nó trước
            if not hasattr(self, 'log_command_input'):
                self.log_command_input = TextArea(
                    height=1,          
                    prompt=">>> ",
                    multiline=False,
                    accept_handler=self.handle_log_command
                )

            self.cmd_frame = Frame(self.log_command_input, title="Input", width=None, height=3)

            self.info_window = HSplit([
                self.info_up_window,
                self.cmd_frame
            ], width=None, height=None)

            self.info_frame = Frame(self.info_window, title="Terminal", width=None, height=None)
        else:
            #self.info_up_window = Window(FormattedTextControl(self.create_info_content), width=None, height=None)
            self.info_window = Window(FormattedTextControl(self.create_info_content), width=None)
            self.info_frame = Frame(self.info_window, title=lambda: f"{self.menu_list[self.selected_item]}")

        main_content = VSplit([
            Frame(self.menu_window, title="Menu"),
            self.info_frame,
            side_container
        ])

        log_window = Window(FormattedTextControl(self._get_log_text), height=1, style='class:frame.label')

        status_bar = VSplit([
            Window(FormattedTextControl("↑↓: Navigate | Enter: Select | Esc: Back | Ctrl+C: Exit"), style='class:status'),
            Window(FormattedTextControl("spaceliintech.com"), align=WindowAlign.RIGHT, style='#1313c2')
        ], height=1)

        # self.write_log(">>>: ")

        return HSplit([header, main_content, Frame(log_window), status_bar])

    
    def run(self):
        self.layout = Layout(container=self.get_container())
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
            mouse_support=False,
            refresh_interval=1 
        )
        
        self.app.run()
    
    def __del__(self):
        # Đóng UART Log
        if getattr(self, "uart_log_file", None):
            try:
                self.uart_log_file.close()
            except Exception:
                pass
        # Đóng Data Log nếu vô tình vẫn mở
        if getattr(self, "data_log_file", None):
            try:
                self.data_log_file.close()
            except Exception:
                pass

def main():
    gui = RaspiGUI()
    gui.run()

if __name__ == "__main__":
    print("\x1b[8;24;80t", end="", flush=True)
    
    main()

