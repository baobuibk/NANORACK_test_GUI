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
import psutil
import re
from tabulate import tabulate
from ThreadSerial import ThreadSerial

class RaspiGUI:

    def __init__(self):
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
            "   Logs   ",
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
                {"key": "CPU Usage", "value": f"{psutil.cpu_percent()}%"},
                {"key": "Memory Usage", "value": f"{psutil.virtual_memory().percent}%"},
            ],
            "Status": [
                {"key": "CPU Usage", "value": f"{psutil.cpu_percent()}%"},
                {"key": "Memory Usage", "value": f"{psutil.virtual_memory().percent}%"},
                {"key": "Disk Usage", "value": f"{psutil.disk_usage('/').percent}%"},
                {"key": "Temperature", "value": f"{self.get_cpu_temperature()}°C"}
            ],
            "PreSetup": [
                {"key": "SSH Service", "value": "Disable"},
                {"key": "Type Connect", "value": "Serial"},
                {"key": "Port", "value": default_com}
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
            "Logs": [
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

        self.menu_list = ["PreSetup","Config","Tracking","Manual","Logs","Option","Quit"]

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
        

        categories = ["Config", "Status", "PreSetup", "Tracking", "Manual", "Logs", "Option", "Quit"]
        for cat in categories:
            filename = f"{cat}.json"
            self.settings_data[cat] = self.load_category_data(filename, default_data[cat])
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

    def get_cpu_temperature(self):
        try:
            return temp.replace("temp=", "").replace("'C\n", "")
        except:
            return "N/A"

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
            #lambda đối số: hàm thực hiện, nó là 1 hàm ẩn danh cũng là 1 hàm callback, ở lệnh trên thì nó chỉ có hàm k có đối số, và hàm lambda không thực hiện ngay mà sẽ được thực hiện khi có sự thay đổi giao diện, do GUI điều khiển, 
            #nên mỗi lần GUI thay đổi nó sẽ tự cập nhật, nếu không có lambda thì nó sẽ thực hiện hàm self.utils_data.get() ngay và không updateupdate
            width=None,
            height=3,
            title='Datetime'
        )
        status_frame = Frame(
            Window(FormattedTextControl("Active"), align=WindowAlign.CENTER),
            width=14, 
            height=3
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
            self.test()
            
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
                    if self.selected_info < len(data):
                        current_field = data[self.selected_info]

                        if selected_key == "Config":
                            config_data = self.settings_data.get("Config", [])
                            apply_index = len(config_data)
                            if self.selected_info == apply_index:
                                # Ghi Config.json
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

                            elif current_field["key"] == "$: >[Send - PhotoDiode Get]":
                                
                                photodiode_index = None
                                for item in data:
                                    if item["key"] == "PhotoDiode Index":
                                        photodiode_index = item["value"]

                                if photodiode_index.isdigit():
                                        try:
                                            self.serial_thread.send_to_port(f"pd_get {photodiode_index}")
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
                                self.test()

                                serial_enabled = False
                                com_port = None
                                for item in data:
                                    if item["key"] == "Type Connect" and item["value"] == "Serial":
                                        serial_enabled = True
                                    if item["key"] == "Port":
                                        com_port = item["value"]
                                if serial_enabled and com_port:
                                    try:

                                        if self.serial_thread:
                                            self.serial_thread.Stop()
                                        self.serial_thread = ThreadSerial( port=com_port, baudrate=115200, timeout= 2)
                                        self.serial_thread.port_connection_found_callback = self.on_serial_connect
                                        self.serial_thread.port_read_callback = self.on_serial_data
                                        self.serial_thread.port_disconnection_callback = self.on_serial_disconnect
                                        threading.Thread(target=self.serial_thread.Start, daemon=True).start()
                                        self.write_log(f">>>: {com_port} Opened, Baudrate: 115200")
                                    except RuntimeError as e:
                                        self.write_log(f">>>: Failed to open port {com_port}: {e}")
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
            self.write_log(">>>: ")

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

        for digit in "0123456789": #tạo biến digit duyệt qua từng số từ 0 đến 9 để đăng kí cho hàm _()
            @self.kb.add(digit)    #bọc cái hàm ở dưới vào trong hàm kb với đối số là digit
            def _(event, digit=digit): #thì event ở đây sẽ là mỗi khi ta nhập 1 số từ bàn phím
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
            #Kiểm tra xem test area có được focus không, ý là để nó biết backspace đang xử lí cho trường hợp nào á, nếu nó đang được focus thì 
            if event.app.layout.has_focus(self.log_command_input):
                buf = self.log_command_input.buffer
                if buf.cursor_position > 0:
                    buf.delete_before_cursor(count=1)
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
        # Phím Tab để chuyển đổi giữa các trường của Set laser
        # @self.kb.add('tab')
        # def _(event):
        #     if self.mode == 'info':
        #         selectable_items = self.get_selectable_items()
        #         if selectable_items[self.selected_item] == "PreSetup":
        #             current_field = self.settings_data["PreSetup"][self.selected_info]
        #             if current_field["key"] == "Set laser":
        #                 if self.editing_field == "set_laser_type":
        #                     self.editing_field = "set_laser_index"
        #                     self.port_buffer = None
        #                 elif self.editing_field == "set_laser_index":
        #                     self.editing_field = "set_laser_dac"
        #                     self.port_buffer = None
        #                 else:
        #                     self.editing_field = "set_laser_type"
        #                     self.port_buffer = None
        #                 event.app.invalidate()      
                
                    
        # @self.kb.add('c-r')
        # def _(event):
        #     self.container = self.get_container()
        #     self.layout.container = self.container
        #     event.app.invalidate()


    def on_serial_connect(self, port, ser):
        self.write_log(f">>>: {port} Opened, Baudrate: {ser.baudrate}")

    def on_serial_data(self, port, ser, data):
        self.write_log( f">>>: Received from {port}: {data}")
        self.write_log(f">>>: Received from {port}: (Length: {len(data)})")


    def on_serial_disconnect(self, port):
        self.write_log(f">>>: Disconnected from {port}")

    def create_menu_content(self):  #Tạo 1 list lồng tuple têntên content để lưu trang thái của cả cái menu, là kiểu đang chọn cái nào thì nó đổi màu cái đó
        content = []          #Nó sẽ lưu thành 1 list nhiều tuple, mỗi tuple là 1 cặp gồm (trạng thái màu, nội dungdung)
        selectable_index = 0  #Biến để chỉ vị trí cần tô sáng

        for item in self.menu_items:
            if self.is_divider(item): 
                content.append(('', item + "\n"))  #nếu nó duyệt thấy là dấu - thì nó sẽ kh có trạng thái màu và nội dung là cái item đó với việc xuống dòng
            else: #nếu nó không phải là các dấu - thì nó là các đề mục của mục menu 
                style = 'class:menu.selected' if selectable_index == self.selected_item else 'bold' #nếu cái index của hàm này bằng với cái self.selected_item, nghĩa là ta đang chọn mục đó thì nó sẽ lưu tuple(với style là class..., nội dung), còn không thì nó chỉ có style là bold
                content.append((style, f"{item}\n"))
                selectable_index += 1
        return content

        
    def get_selectable_items(self):
        return [item.strip() for item in self.menu_items if not self.is_divider(item)]

    
    #Trong hàm dưới đây đã có set title, là nó đặt cái nội dung tiltle ra đè lên cái viền
    def create_info_content(self):
        selectable_items = self.get_selectable_items()       #trả về 1 list không có các dấu "-"
        selected_key = selectable_items[self.selected_item]  #lấy 1 phần tử của list tùy theo cái con trỏ đang nằm ở đâuđâu
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
        
        elif selected_key in ["PreSetup", "Manual"]: #dùng để hiển thị sáng lên cái dòng đang được chọn trong bản infor
            content = [] #tạo 1 tuple lưu text và trạng thái dòng text tương ứng
            if selected_key == "PreSetup":
                content.append(('class:frame.label', f"\n  ---> {selected_key}: \n\n"))#dùng để thêm 1 thành phần tuple là  1 text với trạng thái dòng text ở đây dòng đó là PreSetup và nó cũng được đặt vị trí tiêu đề, chèn lên cái frame
            elif selected_key == "Manual":
                pass

            data = self.settings_data[selected_key]
            for i, item in enumerate(data):  #trả về index và 1 phần tử dict của data
                display_value = f"{item['value']}"
                if selected_key == "PreSetup" and item["key"] == "COM" and display_value:
                    display_value = f"{display_value}"  # Hiển thị trực tiếp COM3, COM4, ...
                if selected_key == "Manual" and i == 0:
                    term_size = os.get_terminal_size()
                    term_width = term_size.columns - 28
                    separator = "---[Laser]"+"-" * term_width + "\n"
                    content.append(('class:info', separator))
                
                if self.selected_info == i and self.mode == 'info':
                    key_style = 'class:info.selected'    #nếu con trỏ đang nằm tại vị trí đó, con trỏ thì nó lưu trong self.selected_info thì nó sẽ lưu cái style nổi bật ở đó
                    value_style = 'class:info.selected'  
                else:
                    if item["key"] == "$: >[Send - Laser Set]" or item["key"] == "$: >[Send - Current Get]"  or item["key"] == "$: >[Send - PhotoDiode Get]" :
                        key_style = 'class:frame.label'
                        value_style = 'class:value'
                    else:
                        key_style = 'class:key'
                        value_style = 'class:value'
                content.append((key_style, f"  {item['key']}: ")) #dòng trên và dòng dưới là nó lưu 1 cặp tuple, cặp thứ nhất là key và trạng thái, cặp thuứ 2 là value và trạng thái, mà ở đây cái key là cái giá trị của cái key thứ nhất và value là giá trị của cái key thứ 2
                content.append((value_style, f"{item['value']}\n"))
                if selected_key == "Manual":
                    self.write_log(f">>>: +{self.selected_info}")
                    term_size = os.get_terminal_size()
                    term_width = term_size.columns - 28
                    separator = "-" * term_width + "\n"

                    if item["key"] == "$: >[Send - Laser Set]":
                        separator = "---[Laser Current]"+"-" * term_width + "\n"
                        content.append(('class:info', separator))

                    if item["key"] == "Laser DAC" or item["key"] == "Current Type" or item["key"] == "PhotoDiode Index":
                        separator = "-" * term_width + "\n"
                        content.append(('class:info', separator))
  
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
            
            
            #đây là chỗ ta sẽ tạo thêm 1 trường hơp nếu nó là logs để cho nó hiển thị cái khuing nhập luioonuioon
            
        elif selected_key == "Tracking":
            content = self.formatted 
            return content

        elif selected_key == "Config":
            content = []
            content.append(('class:frame.label', f"\n  ---> Config:\n\n"))
            config_data = self.settings_data.get("Config", [])

            # Tính term_width để căn chỉnh nội dung (giống cách bạn làm trong PreSetup/Manual)
            term_size = os.get_terminal_size()
            term_width = term_size.columns - 28

            # In từng dòng của config_data: "Sample to get" và "Sample rate"
            for i, field in enumerate(config_data):
                # Nếu đang focus (selected_info) thì highlight
                if self.selected_info == i and self.mode == 'info':
                    key_style = 'class:info.selected'
                    value_style = 'class:info.selected'
                else:
                    key_style = 'class:key'
                    value_style = 'class:value'

                content.append((key_style, f"  {field['key']}: "))
                content.append((value_style, f"{field['value']}\n"))

            # In nút [ Apply ] tương tự như PreSetup/Manual
            apply_index = len(config_data)  # khi selected_info == apply_index sẽ highlight nút
            if self.selected_info == apply_index and self.mode == 'info':
                apply_style = 'class:info.selected'
            else:
                apply_style = 'class:info'
            apply_text = "[ Apply ]".center(term_width)
            content.append((apply_style, apply_text + "\n"))

            ################################################
            # 2) Chèn separator giữa Config và Status      #
            ################################################
            separator = "-" * term_width + "\n"
            content.append(('class:info', separator))

            #########################################
            # 3) In phần Status thật (kết nối UART/SPI, #
            #    và hiển thị expected từ Config.json ) #
            #########################################
            content.append(('class:frame.label', f"\n  ---> Status:\n\n"))

            status_data = self.settings_data.get("Status", [])

            # Tính term_width để căn chỉnh nội dung (giống cách bạn làm trong PreSetup/Manual)
            term_size = os.get_terminal_size()
            term_width = term_size.columns - 28

            # In từng dòng của config_data: "Sample to get" và "Sample rate"
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
        
    
    #Tính giá trị trung bình, xét điều kiện lớn hơn 2 là do bỏ 2 giá trị đầu, kiểm tra những số khác 0 và chỉ lấy trung bình những số đó
    def DAC_avarage (self):
        a = 0
        sum = 0
        for i,value in enumerate(self.output_log_line):
            if (i > 1) and (value != 0):
                sum += value*3.3/16383
                a+=1
            continue
        return f"{sum/a:.2f}" 
    

    #Tiền xủ lý khi đọc từ file.log về
    def process_data(self,log_line):                
        patern = r"C(\d+)-(\d+)"\
                r".*?\[T: 0\]-\[ADC: (\d+)\]"\
                r"(?:.*?\[T: 1\]-\[ADC: (\d+)\])?"\
                r"(?:.*?\[T: 2\]-\[ADC: (\d+)\])?"\
                r"(?:.*?\[T: 3\]-\[ADC: (\d+)\])?"
        match = re.search(patern, log_line)
#patern ở đây là 1 regrex dùng để đối chiếu với 1 hàng trong file log, do mỗi lần ta đọc về từ file.log là ta đọc 1 hàng
#thì ở đây nó trả về 6 cái (\d+) bao gồm hàng, côt, lần lấy 0,1,2,3
#match = re.search() sẽ lưu nó vào matchmatch

        if match:
            self.output_log_line = list(match.groups()) #match.groups() là lấy tất cả những gì có trong match, list() là lưu nó vào 1 biến mới dưới dạng list
            self.output_log_line = [0 if x is None else x for x in self.output_log_line]
            self.output_log_line = list(map(int,self.output_log_line))
            self.sensor_value[self.output_log_line[0]-1][self.output_log_line[1]-1] = self.DAC_avarage()
            #return self.sensor_value
            self.format_table(self.output_log_line[0],self.output_log_line[1])
        
        else:
            print("Không tìm thấy dữ liệu cảm biến!")

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
    def handle_log_command(self, buffer):
        self.text_from_command = buffer.text.strip()
        if self.text_from_command:
            try:
                # Ví dụ các lệnh xử lý
                if self.text_from_command.lower() == "help":
                    if not hasattr(self, 'create_info_log_raw'):
                        #self.create_info_log = None
                        self.create_info_log_raw = []
                        for data in self.recommended_command:
                            self.create_info_log_raw.append("".join(data)+"\n")
                    self.create_logs_log = "".join(self.create_info_log_raw)
                if self.text_from_command.lower() == "clear":
                    self.create_logs_log = None

                
            except Exception as e:
                self.log_command_input.text = f"Error: {str(e)}"

        return True  # Giữ TextArea hoạt động

    def get_container(self):
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
        

        if self.selected_item == 4:
            self.info_up_window = Window(FormattedTextControl(self.create_logs_log), width=None, height=None)
            # Kiểm tra nếu `log_command_input` đã tồn tại, xóa nó trước
            if not hasattr(self, 'cmd_frame'):
                self.cmd_frame = None  

                # Sau đó mới tạo lại từ đầu
                self.log_command_input = TextArea(
                    height=3,
                    prompt=">>> ",
                    multiline=False,
                    accept_handler=self.handle_log_command
                )

            self.cmd_frame = Frame(self.log_command_input, title="Command Line", width=None, height=3)
            text_input = Window(FormattedTextControl(lambda: f"BAN DA NHAP: {self.text_from_command}"), width=None, height=None)

            self.info_window = HSplit([
                self.info_up_window,
                #text_input,
                self.cmd_frame
            ], width=None, height=None)

            self.info_frame = Frame(self.info_window, title="Logs", width=None, height=None)
        else:
            #self.info_up_window = Window(FormattedTextControl(self.create_info_content), width=None, height=None)
            self.info_window = Window(FormattedTextControl(self.create_info_content), width=None)
            self.info_frame = Frame(self.info_window, title=lambda: f"{self.menu_list[self.selected_item]}")

        main_content = VSplit([
            Frame(self.menu_window, title="Menu"),
            self.info_frame,
            Frame(side_window, title="Log")
        ])

        log_window = Window(FormattedTextControl(self._get_log_text), height=1, style='class:frame.label')

        status_bar = VSplit([
            Window(FormattedTextControl("↑↓: Navigate | Enter: Select | Esc: Back | Ctrl+C: Exit"), style='class:status'),
            Window(FormattedTextControl("spaceliintech.com"), align=WindowAlign.RIGHT, style='#1313c2')
        ], height=1)

        # self.write_log(">>>: ")

        return HSplit([header, main_content, Frame(log_window), status_bar])







    #Ở đây vấn đề là do ta gọi cái self.get_container để truyền chỉ 1 lần đầu tiên ta run() nên nó không thể cặp nhật trạng thái bảng dù cho biến selected_item có thay đổi
    #biến đó nó thay đổi thì khi ta dùng event.app.invalidate() thì nó chỉ vẽ lại nội dung thôi còn cái mà layout cái bảng từ self.get_container vẫn cố định do nó đã truyền cố định lúc đầu
    #nên ở đây ta phải chèn vào cái event mà cho nó liên tục cập nhật lại cái self.get_container hay có thể hiểu là gọi cái đó ra nhiều lần thì nó mới check điều kiện tại thời điểm nó gọi xem như nào ròi nó mới thực hiện được
    # 1 sai lầm NGHIÊM TRỌNG là tôi kiểm tra điều kiện trong cái hàm nhưng tôi lại gọi hàm đó có 1 lần:)))  

    
    def run(self):
        self.layout = Layout(container=self.get_container())
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
            mouse_support=True,
            refresh_interval=1 
        )
        
        self.app.run()
    
def main():
    gui = RaspiGUI()
    gui.run()

if __name__ == "__main__":
    print("\x1b[8;24;80t", end="", flush=True)
    
    main()

