from osc_server import OSCServer
from threading import Thread
from queue import Queue, Empty
from shared_resources import normalized_queue
import asyncio
import io
import qrcode
import logging
from config_manager import ConfigManager
from pydglab_ws import FeedbackButton, Channel, RetCode, DGLabWSServer
import time
import copy
import tkinter as tk
from tkinter import scrolledtext, font, ttk
from PIL import Image, ImageTk
from qrcode.image.pil import PilImage

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
config = ConfigManager()

class PulseManager:
    def __init__(self):
        self.data = {
            Channel.A: {'lastdata': [], 'nextdata': []},
            Channel.B: {'lastdata': [], 'nextdata': []}
        }
        self.client_tasks = {}

    async def pulse_task(self, client):
        try:
            while True:
                try:
                    address, normalize = normalized_queue.get_nowait()
                    channel = Channel.A if 'left' in address else Channel.B if 'right' in address else None
                    if channel:
                       await self.process_channel_data(channel, int(normalize), client)
                except Empty:
                    await asyncio.sleep(0.01)  # Short sleep to yield control and prevent busy waiting
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logging.info(f"Pulse task for client {client} was cancelled.")

    async def process_channel_data(self, channel, normalize, client):
        channel_data = self.data[channel]
        if len(channel_data['nextdata']) < 4:
            channel_data['nextdata'].append(normalize)
        else:
            if len(channel_data['lastdata']) > 0:
                logging.info(f"Channel {channel} last: {channel_data['lastdata']}")
                logging.info(f"Channel {channel} next: {channel_data['nextdata']}")
                # Simulate sending data to client
                # Here you would send the data to the specific client
                await client.add_pulses(channel, *[((10, 10, 10, 10), channel_data['lastdata']), ((10, 10, 10, 10), channel_data['nextdata'])])
            channel_data['lastdata'] = copy.copy(channel_data['nextdata'])
            channel_data['nextdata'].clear()

    def start_sending(self, client):
        if client not in self.client_tasks or self.client_tasks[client].done():
            task = asyncio.create_task(self.pulse_task(client))
            self.client_tasks[client] = task
            logging.info(f"Started sending task for client ID: {client.target_id}")

    def stop_sending(self, client):
        if client in self.client_tasks:
            self.client_tasks[client].cancel()
            del self.client_tasks[client]
            logging.info(f"Stopped sending task for client ID: {client.target_id}")

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ケモミミもも郊狼控制台")
        self.root.geometry("1000x600")
        
        # 设置主题样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 配置自定义样式
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', padding=5, font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))
        
        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建左侧面板
        self.left_panel = ttk.Frame(self.main_frame)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 状态面板
        self.status_frame = ttk.LabelFrame(self.left_panel, text="状态信息")
        self.status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.connection_status = ttk.Label(self.status_frame, text="未连接", foreground="red")
        self.connection_status.pack(pady=5)
        
        # 通道状态
        self.channel_frame = ttk.Frame(self.status_frame)
        self.channel_frame.pack(fill=tk.X, padx=5)
        
        self.channel_a_status = ttk.Label(self.channel_frame, text="通道A: 未激活", foreground="gray")
        self.channel_a_status.pack(side=tk.LEFT, padx=5)
        
        self.channel_b_status = ttk.Label(self.channel_frame, text="通道B: 未激活", foreground="gray")
        self.channel_b_status.pack(side=tk.LEFT, padx=5)
        
        # 设置等宽字体
        self.mono_font = font.Font(family="Consolas", size=10)
        
        # 创建日志显示区域
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
        
        # 创建右侧面板
        self.right_panel = ttk.Frame(self.main_frame, width=300)  # 设置固定宽度
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        self.right_panel.pack_propagate(False)  # 防止子组件影响面板大小
        
        # 修改二维码显示区域
        self.qr_frame = ttk.LabelFrame(self.right_panel, text="连接二维码")
        self.qr_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动画布来容纳多个二维码
        self.canvas = tk.Canvas(self.qr_frame)
        self.scrollbar = ttk.Scrollbar(self.qr_frame, orient="vertical", command=self.canvas.yview)
        self.qr_container = ttk.Frame(self.canvas)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.qr_container, anchor="nw")
        
        # 添加鼠标滚轮事件绑定
        self.canvas.bind('<Enter>', lambda e: self.canvas.bind_all('<MouseWheel>', self._on_mousewheel))
        self.canvas.bind('<Leave>', lambda e: self.canvas.unbind_all('<MouseWheel>'))

        # 二维码标签列表
        self.qr_labels = []
        
        # 绑定事件
        self.qr_container.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # 控制按钮
        self.control_frame = ttk.Frame(self.right_panel)
        self.control_frame.pack(fill=tk.X, pady=10)
        
        self.clear_log_btn = ttk.Button(
            self.control_frame,
            text="清除日志",
            command=self.clear_log
        )
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)
        
        # 重定向日志输出到GUI
        self.redirect_logging()
    
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
        
        # 使用 Text 组件替代 Entry，支持自动折行
        url_text = tk.Text(qr_frame, height=2, wrap=tk.WORD)
        url_text.insert('1.0', data)
        url_text.configure(
            state='disabled',  # 使用 disabled 而不是 readonly
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

async def dglab_websocket(gui):
    pulse_manager = PulseManager()
    async with DGLabWSServer(config.host, config.port, 60) as server:
        client = server.new_local_client()
        logging.info("请用 DG-Lab App 扫描二维码以连接")
        for socket_url in config.socket_urls:
           url = client.get_qrcode(socket_url)
           gui.insert_qrcode(url)
           logging.info(f"请扫描二维码连接，或直接使用地址: {url}")
        
        await client.bind()
        gui.update_connection_status(True, client.target_id)
        logging.info(f"已与 App {client.target_id} 成功绑定")

        async for data in client.data_generator(FeedbackButton, RetCode):
            if isinstance(data, FeedbackButton):
                logging.info(f"App 触发了反馈按钮：{data.name}")

            if data == FeedbackButton.A1:
                logging.info("对方按下了 A 通道圆圈按钮，开始发送波形")
                gui.update_channel_status(Channel.A, True)
                pulse_manager.start_sending(client)

            elif data == FeedbackButton.A2:
                logging.info("对方按下了 A 通道暂停按钮，暂停发送波形")
                gui.update_channel_status(Channel.A, False)
                pulse_manager.stop_sending(client)

            elif data == FeedbackButton.B1:
                logging.info("对方按下了 B 通道圆圈按钮，开始发送波形")
                gui.update_channel_status(Channel.B, True)
                pulse_manager.start_sending(client)

            elif data == FeedbackButton.B2:
                logging.info("对方按下了 B 通道暂停按钮，暂停发送波形")
                gui.update_channel_status(Channel.B, False)
                pulse_manager.stop_sending(client)

            elif data == RetCode.CLIENT_DISCONNECTED:
                logging.info("App 已断开连接，你可以尝试重新扫码进行连接绑定")
                gui.update_connection_status(False)
                gui.update_channel_status(Channel.A, False)
                gui.update_channel_status(Channel.B, False)
                pulse_manager.stop_sending(client)
                await client.rebind()
                gui.update_connection_status(True, client.target_id)
                logging.info("重新绑定成功")

async def main(gui):
    ip = config.osc_host
    port = config.osc_port

    osc_server = OSCServer(ip, port)
    osc_server.start()

    await dglab_websocket(gui)

if __name__ == "__main__":
    root = tk.Tk()
    gui = AppGUI(root)
    
    def run_asyncio():
        asyncio.run(main(gui))

    import threading
    threading.Thread(target=run_asyncio, daemon=True).start()
    
    root.mainloop()