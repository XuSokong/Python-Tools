import os
import ftplib
from ftplib import FTP
import time
import schedule
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
import threading
import queue
import json


def set_ftp_timeout(ftp, timeout=300):
    """设置FTP连接超时时间"""
    ftp.sock.settimeout(timeout)



def upload_file_with_retry(ftp, local_path, remote_name, max_retries=3, log_queue=None, progress_callback=None):
    """带重试机制的文件上传"""
    def log(message):
        if log_queue:
            log_queue.put(message)
        else:
            print(message)
            
    retries = 0
    while retries < max_retries:
        try:
            # 获取文件大小
            file_size = os.path.getsize(local_path)
            uploaded_size = 0
            
            def callback(data):
                nonlocal uploaded_size
                uploaded_size += len(data)
                if progress_callback:
                    progress_callback(local_path, uploaded_size, file_size)
            
            with open(local_path, 'rb') as file:
                ftp.storbinary(f'STOR {remote_name}', file, callback=callback)
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已上传文件: {local_path}")
            return True
        except (ftplib.error_temp, ftplib.error_perm, OSError) as e:
            retries += 1
            if retries >= max_retries:
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 上传文件 {local_path} 失败，已达最大重试次数: {str(e)}")
                return False
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 上传文件 {local_path} 失败，正在重试 ({retries}/{max_retries}): {str(e)}")
            time.sleep(2)  # 等待2秒后重试
        except Exception as e:
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 上传文件 {local_path} 发生未知错误: {str(e)}")
            return False



def upload_directory(ftp, local_dir, remote_dir, log_queue=None, progress_callback=None):
    """递归上传本地目录到FTP服务器，增加超时处理"""
    def log(message):
        if log_queue:
            log_queue.put(message)
        else:
            print(message)
            
    try:
        # 尝试切换到远程目录，如果不存在则创建
        ftp.cwd(remote_dir)
    except ftplib.error_perm:
        # 目录不存在，创建它
        try:
            ftp.mkd(remote_dir)
            ftp.cwd(remote_dir)
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 创建远程目录: {remote_dir}")
        except ftplib.error_perm as e:
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 无法创建远程目录 {remote_dir}: {str(e)}")
            return
    except Exception as e:
        log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 访问远程目录 {remote_dir} 时出错: {str(e)}")
        return

    # 遍历本地目录中的所有项目
    try:
        items = os.listdir(local_dir)
        for item in items:
            local_item_path = os.path.join(local_dir, item)
            remote_item_path = f"{remote_dir}/{item}"

            # 每次操作前重置超时时间
            set_ftp_timeout(ftp, 300)

            try:
                if os.path.isfile(local_item_path):
                    # 上传文件
                    upload_file_with_retry(ftp, local_item_path, item, log_queue=log_queue, progress_callback=progress_callback)
                elif os.path.isdir(local_item_path):
                    # 递归上传子目录
                    upload_directory(ftp, local_item_path, remote_item_path, log_queue=log_queue, progress_callback=progress_callback)
            except Exception as e:
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 处理 {local_item_path} 时出错: {str(e)}")
                # 继续处理下一个项目
                continue
    except Exception as e:
        log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 遍历本地目录 {local_dir} 时出错: {str(e)}")



def upload_to_ftp(local_folder_path, remote_base_dir, ftp_config, log_queue=None, progress_callback=None):
    """上传指定文件夹到FTP服务器"""
    def log(message):
        if log_queue:
            log_queue.put(message)
        else:
            print(message)
            
    ftp_host = ftp_config['host']
    ftp_port = ftp_config['port']
    ftp_username = ftp_config['username']
    ftp_password = ftp_config['password']
    max_connection_retries = 3
    connection_retry_delay = 5  # 秒
    start_time = time.time()

    # FTP连接重试
    for connection_attempt in range(max_connection_retries):
        try:
            # 连接到FTP服务器，设置较长的超时时间
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 连接到FTP服务器: {ftp_host}:{ftp_port} (尝试 {connection_attempt + 1}/{max_connection_retries})")
            ftp = FTP()
            ftp.connect(ftp_host, ftp_port, timeout=60)
            ftp.login(ftp_username, ftp_password)

            # 设置为主动模式（禁用被动模式）
            ftp.set_pasv(False)

            # 设置传输超时时间
            set_ftp_timeout(ftp, 300)  # 5分钟超时
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 成功连接到FTP服务器")
            
            # 获取本地文件夹名称作为远程目录名称
            folder_name = os.path.basename(local_folder_path)
            remote_target_dir = f"{remote_base_dir}/{folder_name}"
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始上传文件夹到: {remote_target_dir}")
            
            try:
                # 上传整个文件夹
                upload_directory(ftp, local_folder_path, remote_target_dir, log_queue=log_queue, progress_callback=progress_callback)
                
                end_time = time.time()
                duration = round(end_time - start_time, 2)
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文件夹 {folder_name} 上传完成，耗时 {duration} 秒")
                
                # 关闭连接
                ftp.quit()
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已断开与FTP服务器的连接")
                
                # 返回成功信息
                return {
                    'status': 'success',
                    'folder': local_folder_path,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration
                }
            except Exception as e:
                end_time = time.time()
                duration = round(end_time - start_time, 2)
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 上传过程中发生错误: {str(e)}")
                # 尝试重新连接
                try:
                    ftp.quit()
                except:
                    pass
                if connection_attempt < max_connection_retries - 1:
                    log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 将在 {connection_retry_delay} 秒后重新尝试连接")
                    time.sleep(connection_retry_delay)
                    continue
                else:
                    log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已达到最大连接重试次数")
                    return {
                        'status': 'failed',
                        'folder': local_folder_path,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration': duration,
                        'error': str(e)
                    }

        except ftplib.all_errors as e:
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] FTP连接错误: {str(e)}")
            if connection_attempt < max_connection_retries - 1:
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 将在 {connection_retry_delay} 秒后重新尝试连接")
                time.sleep(connection_retry_delay)
                continue
            else:
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已达到最大连接重试次数")
                return {
                    'status': 'failed',
                    'folder': local_folder_path,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration,
                    'error': str(e)
                }
        except Exception as e:
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 发生错误: {str(e)}")
            if connection_attempt < max_connection_retries - 1:
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 将在 {connection_retry_delay} 秒后重新尝试连接")
                time.sleep(connection_retry_delay)
                continue
            else:
                log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已达到最大连接重试次数")
                return {
                    'status': 'failed',
                    'folder': local_folder_path,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration,
                    'error': str(e)
                }
    
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    return {
        'status': 'failed',
        'folder': local_folder_path,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration': duration,
        'error': '未知错误'
    }



def main():
    """命令行模式主函数"""
    # 配置参数 - 请根据实际情况修改
    ftp_config = {
        'host': "time.sokong.top",  # FTP服务器地址
        'port': 21,                 # FTP端口，通常是21
        'username': "xusokong",     # FTP用户名
        'password': "159357Ftg"     # FTP密码
    }
    
    local_folder_path = r"E:\xusokong\Justintime\python\serial_communication\log"  # 要上传的本地文件夹路径
    remote_base_dir = "/"  # FTP服务器上的基础目录
    upload_interval = 60  # 上传时间间隔（秒）

    # 立即执行一次上传
    upload_to_ftp(local_folder_path, remote_base_dir, ftp_config)

    # 设置定时任务
    schedule.every(upload_interval).seconds.do(upload_to_ftp, local_folder_path, remote_base_dir, ftp_config)
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 定时上传任务已启动，将每 {upload_interval} 秒执行一次")
    print("按 Ctrl+C 停止程序...")

    # 运行定时任务
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 程序已停止")


def save_config(config):
    """保存配置到文件"""
    config_file = "ftp_backup_config.json"
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存配置失败: {str(e)}")
        return False


def load_config():
    """从文件加载配置"""
    config_file = "ftp_backup_config.json"
    default_config = {
        'ftp_config': {
            'host': "time.sokong.top",
            'port': 21,
            'username': "xusokong",
            'password': "159357Ftg"
        },
        'local_folders': [r"E:\xusokong\Justintime\python\serial_communication\log"],
        'remote_base_dir': r"/",
        'upload_interval': 60,
        'upload_history': []
    }
    
    if not os.path.exists(config_file):
        # 如果配置文件不存在，使用默认配置并保存
        save_config(default_config)
        return default_config
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 确保配置包含所有必要的键
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
        
        # 向后兼容：如果存在旧的local_folder_path键，将其转换为列表形式
        if 'local_folder_path' in config and 'local_folders' not in config:
            config['local_folders'] = [config['local_folder_path']]
            del config['local_folder_path']
        
        return config
    except Exception as e:
        print(f"加载配置失败: {str(e)}")
        return default_config


class FTPBackupGUI:
    """FTP备份程序的GUI界面"""
    def __init__(self, root):
        self.root = root
        self.root.title("FTP定时备份工具")
        self.root.geometry("700x500")
        
        # 设置窗口图标（如果有.ico文件可以添加）
        try:
            self.root.iconbitmap(default='backup_icon.ico')
        except:
            pass  # 如果没有图标文件，忽略错误
            
        # 任务状态
        self.is_running = False
        self.schedule_thread = None
        
        # 创建日志队列
        self.log_queue = queue.Queue()
        
        # 创建进度队列
        self.progress_queue = queue.Queue()
        
        # 加载配置
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        
        # 启动日志更新线程
        self.root.after(100, self.update_logs)
        
        # 启动进度更新线程
        self.root.after(100, self.update_progress)
    
    def create_widgets(self):
        """创建GUI控件"""
        # 设置窗口大小和最小尺寸
        self.root.geometry("850x650")
        self.root.minsize(700, 500)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置区域布局改进
        config_frame = ttk.LabelFrame(main_frame, text="配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 本地文件夹选择区域
        folder_group = ttk.LabelFrame(config_frame, text="本地文件夹配置", padding="5")
        folder_group.grid(row=0, column=0, columnspan=4, sticky=tk.EW, pady=5)
        folder_group.grid_columnconfigure(1, weight=1)
        
        # 文件夹列表框
        folder_list_frame = ttk.Frame(folder_group)
        folder_list_frame.grid(row=0, column=1, sticky=tk.NSEW, pady=5, padx=5)
        
        self.folder_listbox = tk.Listbox(folder_list_frame, width=70, height=4, font=('Microsoft YaHei UI', 10))
        self.folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(folder_list_frame, orient=tk.VERTICAL, command=self.folder_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_listbox.config(yscrollcommand=scrollbar.set)
        
        # 添加初始文件夹
        for folder in self.local_folders:
            self.folder_listbox.insert(tk.END, folder)
        
        # 文件夹操作按钮
        folder_button_frame = ttk.Frame(folder_group)
        folder_button_frame.grid(row=0, column=2, sticky=tk.NSEW, pady=5, padx=5)
        
        # 添加文件夹按钮
        add_btn = ttk.Button(folder_button_frame, text="添加", command=self.add_folder, width=10)
        add_btn.pack(fill=tk.X, pady=3)
        add_btn.bind("<Enter>", lambda e: self.show_tooltip("添加要备份的本地文件夹", e))
        add_btn.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # 移除文件夹按钮
        remove_btn = ttk.Button(folder_button_frame, text="移除", command=self.remove_folder, width=10)
        remove_btn.pack(fill=tk.X, pady=3)
        remove_btn.bind("<Enter>", lambda e: self.show_tooltip("移除选中的文件夹", e))
        remove_btn.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # 清空文件夹按钮
        clear_btn = ttk.Button(folder_button_frame, text="清空", command=self.clear_folders, width=10)
        clear_btn.pack(fill=tk.X, pady=3)
        clear_btn.bind("<Enter>", lambda e: self.show_tooltip("清空所有添加的文件夹", e))
        clear_btn.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # FTP配置区域
        ftp_group = ttk.LabelFrame(config_frame, text="FTP服务器配置", padding="5")
        ftp_group.grid(row=1, column=0, columnspan=4, sticky=tk.EW, pady=5)
        ftp_group.grid_columnconfigure(1, weight=1)
        ftp_group.grid_columnconfigure(3, weight=1)
        
        # FTP服务器
        ttk.Label(ftp_group, text="服务器地址:", font=('Microsoft YaHei UI', 10)).grid(row=0, column=0, sticky=tk.E, pady=5, padx=5)
        self.ftp_host_entry = ttk.Entry(ftp_group, width=30, font=('Microsoft YaHei UI', 10))
        self.ftp_host_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        self.ftp_host_entry.insert(0, self.ftp_config['host'])
        
        # FTP端口
        ttk.Label(ftp_group, text="端口:", font=('Microsoft YaHei UI', 10)).grid(row=0, column=2, sticky=tk.E, pady=5, padx=5)
        self.ftp_port_entry = ttk.Entry(ftp_group, width=10, font=('Microsoft YaHei UI', 10))
        self.ftp_port_entry.grid(row=0, column=3, sticky=tk.W, pady=5, padx=5)
        self.ftp_port_entry.insert(0, str(self.ftp_config['port']))
        
        # FTP用户名
        ttk.Label(ftp_group, text="用户名:", font=('Microsoft YaHei UI', 10)).grid(row=1, column=0, sticky=tk.E, pady=5, padx=5)
        self.ftp_username_entry = ttk.Entry(ftp_group, width=30, font=('Microsoft YaHei UI', 10))
        self.ftp_username_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=5)
        self.ftp_username_entry.insert(0, self.ftp_config['username'])
        
        # FTP密码
        ttk.Label(ftp_group, text="密码:", font=('Microsoft YaHei UI', 10)).grid(row=1, column=2, sticky=tk.E, pady=5, padx=5)
        self.ftp_password_entry = ttk.Entry(ftp_group, width=30, show="*", font=('Microsoft YaHei UI', 10))
        self.ftp_password_entry.grid(row=1, column=3, sticky=tk.EW, pady=5, padx=5)
        self.ftp_password_entry.insert(0, self.ftp_config['password'])
        
        # 高级配置区域
        advanced_group = ttk.LabelFrame(config_frame, text="高级配置", padding="5")
        advanced_group.grid(row=2, column=0, columnspan=4, sticky=tk.EW, pady=5)
        advanced_group.grid_columnconfigure(1, weight=1)
        
        # 远程目录
        ttk.Label(advanced_group, text="远程目录:", font=('Microsoft YaHei UI', 10)).grid(row=0, column=0, sticky=tk.E, pady=5, padx=5)
        self.remote_dir_entry = ttk.Entry(advanced_group, width=50, font=('Microsoft YaHei UI', 10))
        self.remote_dir_entry.grid(row=0, column=1, columnspan=3, sticky=tk.EW, pady=5, padx=5)
        self.remote_dir_entry.insert(0, self.remote_base_dir)
        
        # 上传间隔
        ttk.Label(advanced_group, text="上传间隔(秒):", font=('Microsoft YaHei UI', 10)).grid(row=1, column=0, sticky=tk.E, pady=5, padx=5)
        self.interval_entry = ttk.Entry(advanced_group, width=15, font=('Microsoft YaHei UI', 10))
        self.interval_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        self.interval_entry.insert(0, str(self.upload_interval))
        ttk.Label(advanced_group, text="建议设置为300秒以上", font=('Microsoft YaHei UI', 9, 'italic'), foreground='#666666').grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        
        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        button_frame.pack_propagate(False)
        button_frame.config(height=40)
        
        # 添加按钮样式
        style = ttk.Style()
        
        # 统一界面主题
        style.theme_use('clam')  # 使用clam主题作为基础，可以更好地定制样式
        
        # 配置通用按钮样式
        style.configure('TButton', font=('Microsoft YaHei UI', 10, 'bold'), padding=8,
                        borderwidth=1, relief=tk.RAISED)
        
        # 为不同功能的按钮设置不同颜色
        style.configure('Start.TButton', foreground='#0066cc', background='#e6f2ff',
                        bordercolor='#0066cc')
        style.configure('Stop.TButton', foreground='#cc0000', background='#ffe6e6',
                        bordercolor='#cc0000')
        style.configure('Upload.TButton', foreground='#009900', background='#e6ffe6',
                        bordercolor='#009900')
        
        # 设置按钮悬停效果
        style.map('Start.TButton', background=[('active', '#cce6ff')])
        style.map('Stop.TButton', background=[('active', '#ffcccc')])
        style.map('Upload.TButton', background=[('active', '#ccffcc')])
        
        # 配置LabelFrame样式
        style.configure('TLabelFrame', font=('Microsoft YaHei UI', 10, 'bold'),
                        background='#ffffff', foreground='#333333')
        style.configure('TLabelFrame.Label', font=('Microsoft YaHei UI', 10, 'bold'),
                        background='#ffffff', foreground='#333333')
        
        # 配置Progressbar样式
        style.configure('TProgressbar', troughcolor='#e0e0e0', background='#4CAF50',
                        borderwidth=1, relief=tk.FLAT)
        
        # 配置Scrollbar样式
        style.configure('Vertical.TScrollbar', background='#e0e0e0', troughcolor='#f5f5f5',
                        arrowcolor='#666666')
        style.configure('Horizontal.TScrollbar', background='#e0e0e0', troughcolor='#f5f5f5',
                        arrowcolor='#666666')
        
        # 配置Entry样式
        style.configure('TEntry', font=('Microsoft YaHei UI', 10), padding=5,
                        background='#ffffff', bordercolor='#cccccc', relief=tk.FLAT)
        
        # 配置Label样式
        style.configure('TLabel', font=('Microsoft YaHei UI', 10), background='#ffffff',
                        foreground='#333333')
        
        self.start_button = ttk.Button(button_frame, text="开始定时上传", command=self.start_backup, style='Start.TButton', width=18)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=5)
        self.start_button.bind("<Enter>", lambda e: self.show_tooltip("开始定时上传任务", e))
        self.start_button.bind("<Leave>", lambda e: self.hide_tooltip())
        
        self.stop_button = ttk.Button(button_frame, text="停止定时上传", command=self.stop_backup, state=tk.DISABLED, style='Stop.TButton', width=18)
        self.stop_button.pack(side=tk.LEFT, padx=10, pady=5)
        self.stop_button.bind("<Enter>", lambda e: self.show_tooltip("停止当前的定时上传任务", e))
        self.stop_button.bind("<Leave>", lambda e: self.hide_tooltip())
        
        self.upload_now_button = ttk.Button(button_frame, text="立即上传一次", command=self.upload_now, style='Upload.TButton', width=18)
        self.upload_now_button.pack(side=tk.LEFT, padx=10, pady=5)
        self.upload_now_button.bind("<Enter>", lambda e: self.show_tooltip("立即执行一次上传任务", e))
        self.upload_now_button.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text="上传进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=700, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # 进度标签
        self.progress_label = ttk.Label(progress_frame, text="准备上传", 
                                       font=('Microsoft YaHei UI', 10), 
                                       foreground='#333333')
        self.progress_label.pack(anchor=tk.W, pady=5)
        
        # 增加任务状态指示
        self.status_label = ttk.Label(progress_frame, text="状态: 就绪", 
                                     font=('Microsoft YaHei UI', 10, 'italic'), 
                                     foreground='#666666')
        self.status_label.pack(anchor=tk.E, pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, wrap=tk.WORD, 
                                                 font=('Microsoft YaHei UI', 9),
                                                 bg='#f5f5f5', fg='#333333',
                                                 selectbackground='#3366cc', 
                                                 selectforeground='white',
                                                 insertbackground='#333333')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 设置日志文本框的边框
        self.log_text.config(borderwidth=1, relief=tk.SUNKEN)
        
        # 为日志区域添加清空按钮
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        clear_log_btn = ttk.Button(log_control_frame, text="清空日志", 
                                  command=self.clear_logs, 
                                  style='TButton',
                                  width=10)
        clear_log_btn.pack(side=tk.RIGHT)
        
        # 设置配置区域的列权重
        config_frame.grid_columnconfigure(1, weight=1)
    
    def add_folder(self):
        """添加本地文件夹"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            # 检查文件夹是否已存在
            if folder_path not in [self.folder_listbox.get(i) for i in range(self.folder_listbox.size())]:
                self.folder_listbox.insert(tk.END, folder_path)
                self.log(f"已添加文件夹: {folder_path}")
            else:
                self.log(f"文件夹 {folder_path} 已存在")
    
    def remove_folder(self):
        """移除选中的本地文件夹"""
        selected_indices = self.folder_listbox.curselection()
        if selected_indices:
            # 从后向前删除，避免索引变化
            for i in reversed(selected_indices):
                folder_path = self.folder_listbox.get(i)
                self.folder_listbox.delete(i)
                self.log(f"已移除文件夹: {folder_path}")
        else:
            self.log("请先选择要移除的文件夹")
    
    def clear_folders(self):
        """清空所有本地文件夹"""
        if self.folder_listbox.size() > 0:
            self.folder_listbox.delete(0, tk.END)
            self.log("已清空所有文件夹")
        else:
            self.log("文件夹列表已为空")
    
    def get_config(self):
        """获取当前配置"""
        try:
            port = int(self.ftp_port_entry.get())
            interval = int(self.interval_entry.get())
        except ValueError:
            self.log(f"端口和上传间隔必须是数字")
            return None
        
        ftp_config = {
            'host': self.ftp_host_entry.get(),
            'port': port,
            'username': self.ftp_username_entry.get(),
            'password': self.ftp_password_entry.get()
        }
        
        # 获取所有选择的文件夹
        local_folders = [self.folder_listbox.get(i) for i in range(self.folder_listbox.size())]
        remote_base_dir = self.remote_dir_entry.get()
        
        if not local_folders:
            self.log("请添加至少一个本地文件夹")
            return None
        
        # 验证所有文件夹是否存在
        for folder in local_folders:
            if not os.path.isdir(folder):
                self.log(f"文件夹 {folder} 不是有效的路径")
                return None
        
        return ftp_config, local_folders, remote_base_dir, interval
    
    def log(self, message):
        """记录日志"""
        self.log_queue.put(message)
    
    def update_logs(self):
        """更新日志显示"""
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(100, self.update_logs)
    
    def progress_callback(self, file_path, uploaded_size, total_size):
        """进度回调函数"""
        # 将进度信息放入队列
        self.progress_queue.put((file_path, uploaded_size, total_size))
    
    def update_progress(self):
        """更新进度显示"""
        while not self.progress_queue.empty():
            file_path, uploaded_size, total_size = self.progress_queue.get()
            
            # 计算百分比
            progress_percent = (uploaded_size / total_size) * 100 if total_size > 0 else 0
            
            # 更新进度条
            self.progress_bar['value'] = progress_percent
            
            # 更新进度标签
            file_name = os.path.basename(file_path)
            self.progress_label.config(text=f"正在上传: {file_name} ({uploaded_size}/{total_size} 字节，{progress_percent:.1f}%)")
            
            # 如果上传完成，重置进度条
            if uploaded_size >= total_size:
                self.progress_bar['value'] = 0
                self.progress_label.config(text=f"上传完成: {file_name}")
        
        self.root.after(100, self.update_progress)
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("日志已清空")
    
    def show_tooltip(self, text, event=None):
        """显示工具提示"""
        # 如果工具提示已经存在，先销毁
        if hasattr(self, 'tooltip') and self.tooltip:
            self.hide_tooltip()
            
        # 创建工具提示窗口
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)  # 去除窗口边框
        self.tooltip.wm_geometry("+" + str(event.x_root + 10) + "+" + str(event.y_root + 10))
        
        # 创建提示标签
        label = ttk.Label(self.tooltip, text=text, 
                         background="#ffffe0", foreground="#333333", 
                         relief=tk.SOLID, borderwidth=1, 
                         font=('Microsoft YaHei UI', 9))
        label.pack(ipadx=5, ipady=3)
    
    def hide_tooltip(self):
        """隐藏工具提示"""
        if hasattr(self, 'tooltip') and self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
    
    def start_backup(self):
        """开始定时备份任务"""
        config = self.get_config()
        if not config:
            return
        
        ftp_config, local_folders, remote_base_dir, interval = config
        
        # 保存配置
        self.ftp_config = ftp_config
        self.local_folders = local_folders
        self.remote_base_dir = remote_base_dir
        self.upload_interval = interval
        
        # 保存配置到文件
        self.save_config()
        
        # 启动任务线程
        self.is_running = True
        self.schedule_thread = threading.Thread(target=self.run_schedule, daemon=True)
        self.schedule_thread.start()
        
        # 更新按钮状态
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 更新任务状态
        self.status_label.config(text="状态: 运行中", foreground="#009900")
        
        self.log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 定时上传任务已启动，将每 {interval} 秒执行一次")
    
    def stop_backup(self):
        """停止定时备份任务"""
        self.is_running = False
        
        # 清除所有定时任务
        schedule.clear()
        
        # 更新按钮状态
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 更新任务状态
        self.status_label.config(text="状态: 已停止", foreground="#cc0000")
        
        self.log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 定时上传任务已停止")
    
    def upload_now(self):
        """立即执行一次上传"""
        config = self.get_config()
        if not config:
            return
        
        ftp_config, local_folders, remote_base_dir, _ = config
        
        # 启动上传线程
        threading.Thread(target=self.upload_all_folders, 
                        args=(local_folders, remote_base_dir, ftp_config), 
                        daemon=True).start()
    
    def upload_all_folders(self, local_folders, remote_base_dir, ftp_config):
        """上传所有文件夹并记录历史"""
        batch_id = time.strftime('%Y-%m-%d %H:%M:%S')
        batch_results = []
        
        for folder in local_folders:
            self.log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始上传文件夹: {folder}")
            result = upload_to_ftp(folder, remote_base_dir, ftp_config, self.log_queue, self.progress_callback)
            batch_results.append(result)
        
        # 记录上传历史
        self.add_upload_history(batch_id, batch_results)
        
        self.log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 所有文件夹上传完成")
    
    def add_upload_history(self, batch_id, results):
        """添加上传历史记录"""
        history_entry = {
            'batch_id': batch_id,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': results,
            'total_folders': len(results),
            'successful_folders': sum(1 for r in results if r['status'] == 'success'),
            'failed_folders': sum(1 for r in results if r['status'] == 'failed')
        }
        
        # 添加到历史记录，最多保留100条记录
        self.upload_history.append(history_entry)
        if len(self.upload_history) > 100:
            self.upload_history = self.upload_history[-100:]
        
        # 保存历史记录到配置文件
        self.save_config()
        
        self.log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已记录上传历史: {history_entry['successful_folders']}/{history_entry['total_folders']} 个文件夹上传成功")
    
    def load_config(self):
        """加载配置"""
        config = load_config()
        self.ftp_config = config['ftp_config']
        self.local_folders = config['local_folders']
        self.remote_base_dir = config['remote_base_dir']
        self.upload_interval = config['upload_interval']
        self.upload_history = config.get('upload_history', [])
    
    def save_config(self):
        """保存配置"""
        config = {
            'ftp_config': self.ftp_config,
            'local_folders': self.local_folders,
            'remote_base_dir': self.remote_base_dir,
            'upload_interval': self.upload_interval,
            'upload_history': self.upload_history
        }
        if save_config(config):
            self.log("配置已保存")
        else:
            self.log("保存配置失败")
    
    def run_schedule(self):
        """运行定时任务"""
        # 立即执行一次上传
        self.upload_all_folders(self.local_folders, self.remote_base_dir, self.ftp_config)
        
        # 设置定时任务
        schedule.every(self.upload_interval).seconds.do(
            self.upload_all_folders, 
            self.local_folders, 
            self.remote_base_dir, 
            self.ftp_config
        )
        
        # 运行定时任务
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)


def gui_main():
    """GUI模式主函数"""
    root = tk.Tk()
    app = FTPBackupGUI(root)
    root.mainloop()


if __name__ == "__main__":
    # 启动GUI模式
    gui_main()
    # 如果需要命令行模式，可以使用以下代码
    # main()
