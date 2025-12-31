import os
import can
import sys  # 用于获取程序默认路径
import time
import datetime
import threading
import uploadftp
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

class CAN_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN通信工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 路径相关初始化
        self.default_program_dir = self._get_default_program_dir()
        self.local_path_var = tk.StringVar(value=self.default_program_dir)
        
        # 设置中文字体
        self.setup_styles()
        
        # 初始化核心变量
        self.running = False  # CAN总线运行状态
        self.can_bus = None   # CAN总线实例
        self.receive_thread = None  # 接收线程
        
        # 通信参数配置变量
        self.interface_var = tk.StringVar(value="pcan")
        self.channel_var = tk.StringVar(value="PCAN_USBBUS1")
        self.bitrate_var = tk.StringVar(value="100000")
        
        # 发送参数变量
        self.can_id_var = tk.StringVar(value="00F")
        self.data_var = tk.StringVar(value="24 24 00 00 00 01 24 24")
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建主界面组件
        self.create_widgets()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close) # 窗口关闭时的资源清理
    
    def _get_default_program_dir(self):
        try:
            script_path = os.path.abspath(sys.argv[0])
            script_dir = os.path.dirname(script_path)
            return script_dir
        except Exception as e:
            fallback_dir = os.getcwd()
            timestamp = time.strftime("%H:%M:%S")
            self.running_status_display(f"[{timestamp}] 默认路径获取失败：{str(e)}，使用备选路径：{fallback_dir}")
            return fallback_dir
    
    def show_path_settings(self):
        selected_dir = filedialog.askdirectory(
            title="选择本地路径",
            initialdir=self.local_path_var.get()
        )
        
        if selected_dir:
            self.local_path_var.set(selected_dir)
            timestamp = time.strftime("%H:%M:%S")
            success_msg = f"[{timestamp}] 本地路径已设置为：{selected_dir}"
            self.running_status_display(success_msg)
            messagebox.showinfo("路径设置成功", f"本地路径已更新为：\n{selected_dir}\n后续文件（如日志、数据）将默认保存在此目录下")
    
    def setup_styles(self):
        """统一配置界面样式，确保中文显示正常"""
        self.style = ttk.Style()
        try:
            self.style.configure(".", font=('SimHei', 10))
        except tk.TclError:
            self.style.configure(".", font=('Arial Unicode MS', 10))
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        setting_menu = tk.Menu(menubar, tearoff=0)
        setting_menu.add_command(label="通信设置", command=self.show_comm_settings)
        setting_menu.add_separator()
        setting_menu.add_command(label="本地路径设置", command=self.show_path_settings)
        menubar.add_cascade(label="设置", menu=setting_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def show_comm_settings(self):
        """弹出通信设置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("通信设置")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="接口类型:").grid(row=0, column=0, sticky=tk.W, pady=5)
        interface_combo = ttk.Combobox(
            frame, 
            textvariable=self.interface_var, 
            width=15, 
            state="readonly"
        )
        interface_combo['values'] = ["pcan", "usb2can", "kvaser", "vector", "slcan"]
        interface_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(frame, text="通道:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame,textvariable=self.channel_var,width=15).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(frame, text="比特率:").grid(row=2, column=0, sticky=tk.W, pady=5)
        bitrate_combo = ttk.Combobox(frame,textvariable=self.bitrate_var,width=10,state="readonly")
        bitrate_combo['values'] = ["100000", "125000", "250000", "500000", "1000000"]
        bitrate_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="确定", command=dialog.destroy).pack(pady=5)
        
        dialog.update_idletasks()
        x = (self.root.winfo_width()//2 - dialog.winfo_width()//2) + self.root.winfo_x()
        y = (self.root.winfo_height()//2 - dialog.winfo_height()//2) + self.root.winfo_y()
        dialog.geometry(f"+{x}+{y}")
        
        self.root.wait_window(dialog)
    
    def show_about(self):
        """弹出关于对话框"""
        messagebox.showinfo(
            "关于", 
            "CAN通信工具\n版本 1.0\n功能：\n1. CAN总线数据收发\n2. 固定消息快速发送（时间按钮）\n3. 通信参数配置\n4. 本地路径设置（默认程序所在目录）\n5. 自动日志记录功能\n用于CAN总线监控与调试"
        )
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        conn_frame = ttk.Frame(main_frame)  # 控制区
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.connect_btn = ttk.Button(conn_frame,text="连接",command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=10, pady=5)

        # 消息显示区
        transfer_display_frame = ttk.LabelFrame(main_frame, text="消息显示", padding="10")
        transfer_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.message_display = scrolledtext.ScrolledText(
            transfer_display_frame, 
            wrap=tk.WORD, 
            height=15,
            font=('SimHei', 10)
        )
        self.message_display.pack(fill=tk.BOTH, expand=True)
        self.message_display.config(state=tk.DISABLED)
        
        self.running_status = scrolledtext.ScrolledText(
            transfer_display_frame, 
            wrap=tk.WORD, 
            height=4,
            font=('SimHei', 10)
        )
        self.running_status.pack(fill=tk.BOTH, expand=True)
        self.running_status.config(state=tk.DISABLED)
        
        # 发送区
        send_frame = ttk.LabelFrame(main_frame, text="发送消息", padding="10")
        send_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(send_frame, text="CANID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(
            send_frame, 
            textvariable=self.can_id_var, 
            width=10
        ).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(send_frame, text="数据:").grid(row=0, column=2, sticky=tk.W, pady=5)
        ttk.Entry(
            send_frame, 
            textvariable=self.data_var, 
            width=40
        ).grid(row=0, column=3, sticky=tk.W, pady=5, padx=5)
        
        ttk.Button(
            send_frame, 
            text="发送", 
            command=self.can_send_guimessage
        ).grid(row=0, column=4, padx=10, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(
            value=f"状态：未连接CAN总线 | 本地路径：{self.local_path_var.get()[:50]}"
        )
        status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 配置发送区网格自适应
        for col in range(5):
            send_frame.grid_columnconfigure(col, weight=1)
    
    def toggle_connection(self):
        """切换CAN总线连接状态：连接/断开"""
        if not self.running:
            try:
                self.can_bus = can.interface.Bus(
                    interface=self.interface_var.get(),
                    channel=self.channel_var.get(),
                    bitrate=int(self.bitrate_var.get())
                )
                
                self.running = True
                self.connect_btn.config(text="断开")
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                conn_info = f"已连接：{self.interface_var.get()} | 通道：{self.channel_var.get()} | 比特率：{self.bitrate_var.get()} bps"
                self.status_var.set(
                    f"状态：{conn_info} | 本地路径：{self.local_path_var.get()[:50]}"
                )
                self.running_status_display(f"[{timestamp}] {conn_info}")
                
                self.receive_thread = threading.Thread(
                    target=self.can_receive_messages,
                    daemon=True
                )
                self.receive_thread.start()
                
                self.upload_thread = threading.Thread(
                    target=uploadftp.upload,
                    daemon=True
                )
                self.upload_thread.start()
                
                
            except Exception as e:
                timestamp = time.strftime("%H:%M:%S")
                error_msg = f"连接失败：{str(e)}"
                messagebox.showerror("连接错误", error_msg)
                self.running_status_display(f"[{timestamp}] {error_msg}")
        
        else:
            self.running = False
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
            
            self.connect_btn.config(text="连接")
            self.status_var.set(
                f"状态：未连接CAN总线 | 本地路径：{self.local_path_var.get()[:50]}..."
            )
            timestamp = time.strftime("%H:%M:%S")
            self.running_status_display(f"[{timestamp}] CAN总线已断开")
    
    def can_receive_messages(self):
        """接收CAN数据线程：持续接收并显示"""
        while self.running and self.can_bus:
            try:
                message = self.can_bus.recv(1.0)
                if message:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    can_id = f"0x{message.arbitration_id:X}"
                    data_hex = " ".join([f"{b:02X}" for b in message.data])
                    self.receive_messages_display(
                        f"[{timestamp}] 接收: ID={can_id}, 数据={data_hex}, 长度={message.dlc}字节"
                    )
            except Exception as e:
                if self.running:
                    timestamp = time.strftime("%H:%M:%S")
                    self.running_status_display(f"[{timestamp}] 接收错误: {str(e)}")
                time.sleep(1)
    
    def can_send_guimessage(self):
        """GUI手动发送：读取输入框的CAN ID和数据"""
        if not self.running or not self.can_bus:
            messagebox.showwarning("未连接", "请先连接CAN总线！")
            return
        
        try:
            can_id = int(self.can_id_var.get().strip(), 16)
            can_data = self.data_var.get().strip()
            self.can_send_message(can_id, can_data)
        except ValueError as e:
            timestamp = time.strftime("%H:%M:%S")
            error_msg = f"CAN ID格式错误：{str(e)}\n请输入十六进制ID（如00F）"
            messagebox.showerror("格式错误", error_msg)
            self.running_status_display(f"[{timestamp}] {error_msg}")
    
    def can_send_message(self, can_id, can_data):
        """通用发送函数"""
        if not self.running or not self.can_bus:
            messagebox.showwarning("未连接", "请先连接CAN总线！")
            return
        
        try:
            data = [int(byte.strip(), 16) for byte in can_data.split()] if can_data else []
            
            if len(data) > 8:
                raise ValueError("数据长度超过8字节（CAN标准帧最大支持8字节）")
            
            message = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=False
            )
            
            self.can_bus.send(message)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            send_msg = f"[{timestamp}] 发送: ID=0x{can_id:X}, 数据={can_data}, 长度={len(data)}字节"
            self.receive_messages_display(send_msg)
            # 保存发送的消息到日志
        
        except ValueError as e:
            timestamp = time.strftime("%H:%M:%S")
            error_msg = f"数据错误：{str(e)}"
            messagebox.showerror("数据错误", error_msg)
            self.running_status_display(f"[{timestamp}] {error_msg}")
        except can.CanError as e:
            timestamp = time.strftime("%H:%M:%S")
            error_msg = f"发送失败：{str(e)}"
            messagebox.showerror("发送错误", error_msg)
            self.running_status_display(f"[{timestamp}] {error_msg}")
        except Exception as e:
            timestamp = time.strftime("%H:%M:%S")
            error_msg = f"未知错误：{str(e)}"
            messagebox.showerror("错误", error_msg)
            self.running_status_display(f"[{timestamp}] {error_msg}")
    
    def receive_messages_display(self, message):
        """更新“消息显示区”并保存接收记录到日志"""
        self.save_to_log('received', message)
        self.message_display.config(state=tk.NORMAL)
        self.message_display.insert(tk.END, message + "\n")
        self.message_display.see(tk.END)
        self.message_display.config(state=tk.DISABLED)
    
    def running_status_display(self, message):
        """更新“运行状态区”"""
        self.save_to_log('status', message)
        self.running_status.config(state=tk.NORMAL)
        self.running_status.insert(tk.END, message + "\n")
        self.running_status.see(tk.END)
        self.running_status.config(state=tk.DISABLED)
    
    def ensure_folder_exists(self, folder_name):
        """确保文件夹存在，如果不存在则创建"""
        try:
            folder_path = os.path.join(self.local_path_var.get(), folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                self.running_status_display(f"已创建文件夹: {folder_path}")
            return folder_path
        except Exception as e:
            error_msg = f"创建文件夹失败: {str(e)}"
            self.running_status_display(f"{error_msg}")
            return None
        
    def save_to_log(self, log_name, content):
        """保存内容到指定类型的日志文件"""  
        try:
            # 获取当前日期作为日志文件的一部分
            log_timestamp = datetime.datetime.now().strftime("%Y%m%d")
            # 确保log文件夹存在
            log_path = self.ensure_folder_exists('log')
            if not log_path:
                return
            
            filename = os.path.join(log_path, f"{log_timestamp}_{log_name}.log") 
                
            # 添加详细时间戳
            log_entry = f"{content}\n"
            
            # 写入文件
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            error_msg = f"日志保存失败: {str(e)}"
            self.running_status_display(f"{error_msg}")

    def on_close(self):
        """窗口关闭：清理资源"""
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1.0)
        if self.can_bus:
            self.can_bus.shutdown()
        timestamp = time.strftime("%H:%M:%S")
        exit_msg = f"[{timestamp}] 程序退出，当前本地路径：{self.local_path_var.get()}"
        self.running_status_display(exit_msg)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CAN_GUI(root)
    root.mainloop()
