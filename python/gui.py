import tkinter as tk
from tkinter import scrolledtext, font, ttk
from PIL import Image, ImageTk
import qrcode
import logging
from pydglab_ws import Channel

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ケモミミもも郊狼控制台")
        self.root.geometry("1000x600")
        
        self._setup_styles()
        self._create_main_layout()
        self._setup_left_panel()
        self._setup_right_panel()
        
        # 重定向日志输出到GUI
        self.redirect_logging()

    def _setup_styles(self):
        """设置UI主题和样式"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', padding=5, font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))
        self.mono_font = font.Font(family="Consolas", size=10)

    def _create_main_layout(self):
        """创建主布局"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _setup_left_panel(self):
        """设置左侧面板"""
        self.left_panel = ttk.Frame(self.main_frame)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self._create_status_section()
        self._create_log_section()

    def _create_status_section(self):
        """创建状态信息区域"""
        self.status_frame = ttk.LabelFrame(self.left_panel, text="状态信息")
        self.status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.connection_status = ttk.Label(self.status_frame, text="未连接", foreground="red")
        self.connection_status.pack(pady=5)
        
        self._create_channel_status()

    def _create_channel_status(self):
        """创建通道状态显示"""
        self.channel_frame = ttk.Frame(self.status_frame)
        self.channel_frame.pack(fill=tk.X, padx=5)
        
        self.channel_a_status = ttk.Label(self.channel_frame, text="通道A: 未激活", foreground="gray")
        self.channel_a_status.pack(side=tk.LEFT, padx=5)
        
        self.channel_b_status = ttk.Label(self.channel_frame, text="通道B: 未激活", foreground="gray")
        self.channel_b_status.pack(side=tk.LEFT, padx=5)

    def _create_log_section(self):
        """创建日志显示区域"""
        self.log_frame = ttk.LabelFrame(self.left_panel, text="日志")
        self.log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(
            self.log_frame,
            state='disabled',
            font=self.mono_font,
            background='#ffffff',
            wrap=tk.WORD
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _setup_right_panel(self):
        """设置右侧面板"""
        self.right_panel = ttk.Frame(self.main_frame, width=300)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        self.right_panel.pack_propagate(False)
        
        self._create_qr_section()
        self._create_control_section()

    def _create_qr_section(self):
        """创建二维码显示区域"""
        self.qr_frame = ttk.LabelFrame(self.right_panel, text="连接二维码")
        self.qr_frame.pack(fill=tk.BOTH, expand=True)
        
        self._setup_qr_canvas()
        self.qr_labels = []

    def _setup_qr_canvas(self):
        """设置二维码画布和滚动条"""
        self.canvas = tk.Canvas(self.qr_frame)
        self.scrollbar = ttk.Scrollbar(self.qr_frame, orient="vertical", command=self.canvas.yview)
        self.qr_container = ttk.Frame(self.canvas)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.qr_container, anchor="nw")
        
        # 绑定事件
        self.canvas.bind('<Enter>', lambda e: self.canvas.bind_all('<MouseWheel>', self._on_mousewheel))
        self.canvas.bind('<Leave>', lambda e: self.canvas.unbind_all('<MouseWheel>'))
        self.qr_container.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _create_control_section(self):
        """创建控制按钮区域"""
        self.control_frame = ttk.Frame(self.right_panel)
        self.control_frame.pack(fill=tk.X, pady=10)
        
        self.clear_log_btn = ttk.Button(
            self.control_frame,
            text="清除日志",
            command=self.clear_log
        )
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)

    def clear_log(self):
        self.log_area.configure(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state='disabled')
    
    def update_connection_status(self, connected, client_id=None):
        if connected:
            self.connection_status.config(text=f"已连接 (ID: {client_id})", foreground="green")
        else:
            self.connection_status.config(text="未连接", foreground="red")
    
    def update_channel_status(self, channel, active):
        if channel == Channel.A:
            self.channel_a_status.config(
                text=f"通道A: {'激活' if active else '未激活'}",
                foreground="green" if active else "gray"
            )
        else:
            self.channel_b_status.config(
                text=f"通道B: {'激活' if active else '未激活'}",
                foreground="green" if active else "gray"
            )

    def redirect_logging(self):
        class LogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.configure(state='disabled')
                self.text_widget.yview(tk.END)

        log_handler = LogHandler(self.log_area)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(log_handler)

    def _on_frame_configure(self, event=None):
        """更新画布的滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """当画布大小改变时，调整内部框架的宽度"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def insert_qrcode(self, data):
        """生成并显示二维码"""
        # 创建新的二维码框架
        qr_frame = ttk.Frame(self.qr_container)
        qr_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,  # 稍微减小二维码大小
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # 创建PIL图像
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image = qr_image.resize((150, 150), Image.LANCZOS)  # 调整大小
        photo = ImageTk.PhotoImage(qr_image)
        
        # 创建标签显示二维码
        qr_label = ttk.Label(qr_frame, image=photo)
        qr_label.image = photo
        qr_label.pack(pady=(0, 5))
        
        url_text = tk.Text(qr_frame, height=2, wrap=tk.WORD)
        url_text.insert('1.0', data)
        url_text.configure(
            state='disabled', 
            background='#f0f0f0',
            relief='flat',
            font=('Helvetica', 9)
        )
        url_text.tag_configure('center', justify='center')
        url_text.tag_add('center', '1.0', 'end')
        url_text.pack(pady=(0, 5), fill=tk.X, padx=5)
        
        # 添加分隔线（除了最后一个二维码）
        separator = ttk.Separator(qr_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=5)
        
        # 修改存储的组件引用
        self.qr_labels.append((qr_label, url_text))
        logging.info(f"二维码URL: {data}")

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")