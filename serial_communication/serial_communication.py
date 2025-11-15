import serial
import serial.tools.list_ports
import threading
import time
import sys
import platform
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

class RS485Terminal:
    def __init__(self, gui_callback=None):
        self.ser = None
        self.running = False
        self.receive_thread = None
        self.echo = True  # 是否回显发送的数据
        self.hex_mode = True  # 默认使用十六进制模式
        self.gui_callback = gui_callback  # 用于更新GUI的回调函数
        
    def list_ports(self):
        """列出所有可用的串口 - 跨平台支持"""
        ports = serial.tools.list_ports.comports()
        port_list = []
        
        for port in ports:
            # 提供更详细的端口信息，方便识别
            port_info = f"{port.device}"
            if port.description and port.description != port.device:
                port_info += f" - {port.description}"
            port_list.append(port_info)
        
        # 如果没有找到端口，返回空列表
        return port_list if port_list else []
    
    def connect(self, port, baudrate=9600, parity=serial.PARITY_NONE, 
                stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0.1):
        """连接到指定的串口"""
        try:
            # 提取实际端口名（去除描述信息）
            actual_port = port.split(' - ')[0] if ' - ' in port else port
            
            self.ser = serial.Serial(
                port=actual_port,
                baudrate=baudrate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                timeout=timeout,
                rtscts=False,
                dsrdtr=False
            )
            
            if self.ser.is_open:
                self.running = True
                self.start_receive_thread()
                return True, f"已连接到 {actual_port}，波特率: {baudrate}"
            return False, "无法打开串口"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def start_receive_thread(self):
        """启动接收数据的线程"""
        self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.receive_thread.start()
    
    def receive_data(self):
        """接收数据的线程函数"""
        while self.running and self.ser and self.ser.is_open:
            try:
                data = self.ser.read(1)
                if data:
                    # 继续读取可能剩余的数据
                    while self.ser.in_waiting:
                        data += self.ser.read(self.ser.in_waiting)
                    
                    timestamp = time.strftime("%H:%M:%S")
                    
                    if self.hex_mode:
                        # 以十六进制显示
                        hex_str = ' '.join(f'{b:02X}' for b in data)
                        display_text = f"[{timestamp}] 收到: [{len(data)} bytes] {hex_str}\n"
                    else:
                        # 尝试以ASCII显示
                        try:
                            str_data = data.decode('utf-8', errors='replace')
                            display_text = f"[{timestamp}] 收到: [{len(data)} bytes] {str_data}\n"
                        except:
                            hex_str = ' '.join(f'{b:02X}' for b in data)
                            display_text = f"[{timestamp}] 收到: [{len(data)} bytes] (非ASCII) {hex_str}\n"
                    
                    # 通过回调更新GUI
                    if self.gui_callback:
                        self.gui_callback(display_text, is_received=True)
            except Exception as e:
                error_msg = f"[{time.strftime('%H:%M:%S')}] 接收错误: {str(e)}\n"
                if self.gui_callback:
                    self.gui_callback(error_msg, is_error=True)
                break
            time.sleep(0.01)
    
    def send_data(self, data):
        """发送数据"""
        if not self.ser or not self.ser.is_open:
            return False, "未连接到串口"
        
        try:
            if self.hex_mode:
                # 处理十六进制数据
                data = data.replace(' ', '')
                if len(data) % 2 != 0:
                    data += '0'  # 补全为偶数长度
                send_bytes = bytes.fromhex(data)
            else:
                # 处理字符串数据
                send_bytes = data.encode('utf-8')
            
            self.ser.write(send_bytes)
            return True
        except Exception as e:
            return False, f"发送错误: {str(e)}"
    
    def close(self):
        """关闭连接"""
        self.running = False
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
            return True, "已关闭串口连接"
        return False, "没有打开的串口连接"
    
    def toggle_hex_mode(self):
        """切换十六进制模式"""
        self.hex_mode = not self.hex_mode
        return self.hex_mode
    
    def toggle_echo(self):
        """切换回显模式"""
        self.echo = not self.echo
        return self.echo


class RS485GUITerminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RS485 终端")
        
        # 根据操作系统调整初始窗口大小
        system = platform.system()
        if system == 'Darwin':  # macOS
            self.geometry("900x650")
        else:
            self.geometry("800x600")
        
        self.minsize(600, 400)
        
        # 自动最大化窗口
        self.maximize_window()
        
        # 创建终端核心实例
        self.terminal = RS485Terminal(gui_callback=self.update_display)
        
        # 设置中文字体支持（在创建组件之前）
        self.setup_fonts()
        
        # 创建界面组件
        self.create_widgets()
        
        # 初始化端口列表
        self.refresh_port_list()
    
    def get_system_info(self):
        """获取系统信息用于调试"""
        return f"{platform.system()} {platform.release()} ({platform.machine()})"
    
    def maximize_window(self):
        """跨平台窗口最大化"""
        system = platform.system()
        
        try:
            if system == 'Windows':
                # Windows系统
                self.state('zoomed')
            elif system == 'Darwin':
                # macOS系统 - 使用全屏模式
                self.attributes('-zoomed', True)
            else:
                # Linux和其他系统
                try:
                    # 尝试使用zoomed状态
                    self.state('zoomed')
                except:
                    # 如果失败，使用屏幕尺寸设置窗口大小
                    screen_width = self.winfo_screenwidth()
                    screen_height = self.winfo_screenheight()
                    self.geometry(f"{screen_width}x{screen_height}+0+0")
        except Exception as e:
            # 如果最大化失败，使用默认窗口大小
            pass
        
    def setup_fonts(self):
        """设置支持中文的字体 - 跨平台"""
        system = platform.system()
        
        # 根据操作系统选择合适的字体
        if system == 'Windows':
            default_font = ('Microsoft YaHei', 10)  # 微软雅黑
        elif system == 'Darwin':  # macOS
            default_font = ('PingFang SC', 12)  # 苹方
        else:  # Linux and others
            # 尝试常见的Linux中文字体
            try:
                import tkinter.font as tkfont
                available_fonts = tkfont.families()
                # 优先级列表
                preferred_fonts = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 
                                 'Noto Sans', 'DejaVu Sans', 'Liberation Sans']
                for font in preferred_fonts:
                    if font in available_fonts:
                        default_font = (font, 10)
                        break
                else:
                    default_font = ('TkDefaultFont', 10)
            except:
                default_font = ('TkDefaultFont', 10)
        
        self.option_add("*Font", default_font)
    
    def create_widgets(self):
        """创建所有GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 串口设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="串口设置", padding="5")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 端口选择
        ttk.Label(settings_frame, text="端口:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(settings_frame, textvariable=self.port_var, width=20, state='readonly')
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 波特率选择
        ttk.Label(settings_frame, text="波特率:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.baudrate_var = tk.StringVar(value="9600")
        baudrate_values = ["9600", "19200", "38400", "57600", "115200", "230400","921600"]
        self.baudrate_combo = ttk.Combobox(settings_frame, textvariable=self.baudrate_var, 
                                          values=baudrate_values, width=10)
        self.baudrate_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # 数据位选择
        ttk.Label(settings_frame, text="数据位:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.bytesize_var = tk.StringVar(value="8")
        bytesize_values = ["5", "6", "7", "8"]
        self.bytesize_combo = ttk.Combobox(settings_frame, textvariable=self.bytesize_var, 
                                         values=bytesize_values, width=5)
        self.bytesize_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        # 停止位选择
        ttk.Label(settings_frame, text="停止位:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.stopbits_var = tk.StringVar(value="1")
        stopbits_values = ["1", "1.5", "2"]
        self.stopbits_combo = ttk.Combobox(settings_frame, textvariable=self.stopbits_var, 
                                         values=stopbits_values, width=5)
        self.stopbits_combo.grid(row=0, column=7, padx=5, pady=5, sticky=tk.W)
        
        # 校验位选择
        ttk.Label(settings_frame, text="校验位:").grid(row=0, column=8, padx=5, pady=5, sticky=tk.W)
        self.parity_var = tk.StringVar(value="无")
        parity_values = ["无", "奇校验", "偶校验", "标记", "空格"]
        self.parity_combo = ttk.Combobox(settings_frame, textvariable=self.parity_var, 
                                       values=parity_values, width=6)
        self.parity_combo.grid(row=0, column=9, padx=5, pady=5, sticky=tk.W)
        
        # 刷新端口按钮
        self.refresh_btn = ttk.Button(settings_frame, text="刷新", command=self.refresh_port_list)
        self.refresh_btn.grid(row=0, column=10, padx=5, pady=5)
        
        # 连接/断开按钮
        self.connect_btn = ttk.Button(settings_frame, text="连接", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=11, padx=5, pady=5)
        
        # 状态显示区域
        status_display_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="5")
        status_display_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_text = scrolledtext.ScrolledText(status_display_frame, wrap=tk.WORD, 
                                                     state=tk.DISABLED, height=4)
        self.status_text.pack(fill=tk.BOTH, expand=False)
        
        # 配置状态文本颜色标签
        self.status_text.tag_config("info", foreground="blue")
        self.status_text.tag_config("success", foreground="green")
        self.status_text.tag_config("error", foreground="red")
        self.status_text.tag_config("warning", foreground="orange")
        
        # 数据显示区域
        display_frame = ttk.LabelFrame(main_frame, text="数据显示", padding="5")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.display_text = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, state=tk.DISABLED, height=4)
        self.display_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置数据文本颜色标签
        self.display_text.tag_config("received", foreground="blue")
        self.display_text.tag_config("sent", foreground="green")
        
        # 模式控制区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 十六进制模式复选框
        self.hex_mode_var = tk.BooleanVar(value=True)
        self.hex_mode_check = ttk.Checkbutton(control_frame, text="十六进制模式", 
                                            variable=self.hex_mode_var, 
                                            command=self.toggle_hex_mode)
        self.hex_mode_check.pack(side=tk.LEFT, padx=10)
        
        # 回显模式复选框
        self.echo_var = tk.BooleanVar(value=True)
        self.echo_check = ttk.Checkbutton(control_frame, text="回显发送数据", 
                                        variable=self.echo_var, 
                                        command=self.toggle_echo)
        self.echo_check.pack(side=tk.LEFT, padx=10)
        
        # 清除显示按钮
        self.clear_btn = ttk.Button(control_frame, text="清除显示", command=self.clear_display)
        self.clear_btn.pack(side=tk.RIGHT, padx=10)
        
        # 数据发送区域
        send_frame = ttk.LabelFrame(main_frame, text="发送数据", padding="5")
        send_frame.pack(fill=tk.BOTH, expand=False)
        
        self.send_entry = scrolledtext.ScrolledText(send_frame, wrap=tk.WORD, height=1)
        self.send_entry.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))
        self.send_entry.focus_set()
        
        # 发送按钮
        self.send_btn = ttk.Button(send_frame, text="发送", command=self.send_data)
        self.send_btn.pack(side=tk.RIGHT, padx=5, pady=5, ipady=20)
        
        # 绑定Enter键发送数据
        self.send_entry.bind("<Return>", lambda event: self.send_data())
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪 - 未连接")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def refresh_port_list(self):
        """刷新可用端口列表"""
        current_port = self.port_var.get()
        port_list = self.terminal.list_ports()
        self.port_combo['values'] = port_list
        
        # 如果没有可用端口，提示用户
        if not port_list:
            self.port_combo['values'] = ["未找到可用端口"]
            self.port_var.set("未找到可用端口")
            self.update_status("未找到可用串口", "warning")
            return
        
        # 如果之前选择的端口仍然存在，则保持选中
        if current_port and any(current_port in p for p in port_list):
            # 查找匹配的端口
            for port in port_list:
                if current_port in port or port.startswith(current_port.split(' - ')[0]):
                    self.port_var.set(port)
                    self.update_status(f"端口列表已刷新，找到 {len(port_list)} 个端口", "info")
                    return
        
        # 否则选择第一个端口
        self.port_var.set(port_list[0])
        self.update_status(f"端口列表已刷新，找到 {len(port_list)} 个端口", "info")
    
    def toggle_connection(self):
        """切换连接状态（连接/断开）"""
        if self.terminal.ser and self.terminal.ser.is_open:
            # 断开连接
            success, msg = self.terminal.close()
            self.status_var.set(msg)
            self.connect_btn.config(text="连接")
            self.update_status(msg, "warning")
        else:
            # 建立连接
            port = self.port_var.get()
            if not port or port == "未找到可用端口":
                messagebox.showerror("错误", "请选择一个有效的端口")
                self.update_status("连接失败：未选择有效端口", "error")
                return
            
            try:
                baudrate = int(self.baudrate_var.get())
                bytesize = int(self.bytesize_var.get())
                
                # 转换停止位
                stopbits_str = self.stopbits_var.get()
                if stopbits_str == "1":
                    stopbits = serial.STOPBITS_ONE
                elif stopbits_str == "1.5":
                    stopbits = serial.STOPBITS_ONE_POINT_FIVE
                else:  # "2"
                    stopbits = serial.STOPBITS_TWO
                
                # 转换校验位
                parity_str = self.parity_var.get()
                if parity_str == "无":
                    parity = serial.PARITY_NONE
                elif parity_str == "奇校验":
                    parity = serial.PARITY_ODD
                elif parity_str == "偶校验":
                    parity = serial.PARITY_EVEN
                elif parity_str == "标记":
                    parity = serial.PARITY_MARK
                else:  # "空格"
                    parity = serial.PARITY_SPACE
                
                # 连接串口
                success, msg = self.terminal.connect(
                    port=port,
                    baudrate=baudrate,
                    parity=parity,
                    stopbits=stopbits,
                    bytesize=bytesize
                )
                
                self.status_var.set(msg)
                
                if success:
                    self.connect_btn.config(text="断开")
                    self.update_status(msg, "success")
                else:
                    self.update_status(msg, "error")
            except Exception as e:
                error_msg = f"参数错误: {str(e)}"
                messagebox.showerror("错误", error_msg)
                self.update_status(error_msg, "error")
    
    def toggle_hex_mode(self):
        """切换十六进制模式"""
        new_mode = self.terminal.toggle_hex_mode()
        self.hex_mode_var.set(new_mode)
        mode_text = "十六进制" if new_mode else "ASCII"
        self.update_status(f"已切换到{mode_text}模式", "info")
    
    def toggle_echo(self):
        """切换回显模式"""
        new_mode = self.terminal.toggle_echo()
        self.echo_var.set(new_mode)
        mode_text = "开启" if new_mode else "关闭"
        self.update_status(f"回显模式已{mode_text}", "info")
    
    def update_display(self, text, is_received=False, is_error=False):
        """更新数据显示区域内容（仅显示收发数据）"""
        self.display_text.config(state=tk.NORMAL)
        
        # 根据数据类型添加颜色标签
        if is_received:
            self.display_text.insert(tk.END, text, "received")
        elif is_error:
            # 错误信息显示到状态栏，不显示在数据区
            self.update_status(text, "error")
            self.display_text.config(state=tk.DISABLED)
            return
        else:
            self.display_text.insert(tk.END, text, "sent")
        
        # 自动滚动到底部
        self.display_text.see(tk.END)
        self.display_text.config(state=tk.DISABLED)
    
    def update_status(self, text, msg_type="info"):
        """更新状态显示区域
        msg_type: info, success, error, warning
        """
        timestamp = time.strftime("%H:%M:%S")
        status_msg = f"[{timestamp}] {text}"
        if not status_msg.endswith('\n'):
            status_msg += '\n'
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, status_msg, msg_type)
        
        # 自动滚动到底部
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def clear_display(self):
        """清除数据显示区域内容"""
        self.display_text.config(state=tk.NORMAL)
        self.display_text.delete(1.0, tk.END)
        self.display_text.config(state=tk.DISABLED)
        self.update_status("数据显示已清除", "info")
    
    def send_data(self):
        """发送数据"""
        data = self.send_entry.get(1.0, tk.END).strip()
        if not data:
            return
        
        # 清空输入框
        #self.send_entry.delete(1.0, tk.END)
        
        result = self.terminal.send_data(data)
        
        # 如果发送失败，显示错误信息
        if isinstance(result, tuple) and not result[0]:
            self.update_status(f"发送失败: {result[1]}", "error")
            return
        
        # 如果回显模式开启，显示发送的数据
        if self.terminal.echo:
            if self.terminal.hex_mode:
                data_clean = data.replace(' ', '')
                if len(data_clean) % 2 != 0:
                    data_clean += '0'
                try:
                    send_bytes = bytes.fromhex(data_clean)
                    hex_str = ' '.join(f'{b:02X}' for b in send_bytes)
                    self.update_display(f"[{time.strftime('%H:%M:%S')}] 发送: [{len(send_bytes)} bytes] {hex_str}\n")
                    self.update_status(f"发送 {len(send_bytes)} 字节数据", "success")
                except ValueError as e:
                    self.update_status(f"十六进制格式错误: {str(e)}", "error")
            else:
                self.update_display(f"[{time.strftime('%H:%M:%S')}] 发送: {data}\n")
                self.update_status(f"发送 {len(data.encode('utf-8'))} 字节数据", "success")
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if self.terminal.ser and self.terminal.ser.is_open:
            self.terminal.close()
            self.update_status("程序正在关闭...", "info")
        self.destroy()


if __name__ == "__main__":
    try:
        app = RS485GUITerminal()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        print(f"程序错误: {str(e)}")
        sys.exit(1)
