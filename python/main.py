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
from tkinter import scrolledtext, font

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
            logging.info(f"Started sending task for client {client}.")

    def stop_sending(self, client):
        if client in self.client_tasks:
            self.client_tasks[client].cancel()
            del self.client_tasks[client]
            logging.info(f"Stopped sending task for client {client}.")

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ケモミミもも郊狼控制台")
        
        # 设置等宽字体
        self.mono_font = font.Font(family="Courier", size=10)
        
        # 创建日志显示区域
        self.log_area = scrolledtext.ScrolledText(root, state='disabled', font=self.mono_font)
        self.log_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 重定向日志输出到GUI
        self.redirect_logging()

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

    def insert_qrcode(self, data):
        """生成 ASCII 格式的二维码并插入到日志文本中"""
        qr = qrcode.QRCode()
        qr.add_data(data)
        qr.make(fit=True)

        # 生成 ASCII 格式的二维码
        f = io.StringIO()
        qr.print_ascii(out=f, invert=False)  
        f.seek(0)
        ascii_qr = f.read()

        # 在日志文本中插入二维码
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, "二维码:\n")
        self.log_area.insert(tk.END, ascii_qr + '\n')
        self.log_area.configure(state='disabled')
        self.log_area.yview(tk.END)  # 自动滚动到底部

async def dglab_websocket(gui):
    pulse_manager = PulseManager()
    async with DGLabWSServer(config.host, config.port, 60) as server:
        client = server.new_local_client()
        logging.info("请用 DG-Lab App 扫描二维码以连接")
        for socket_url in config.socket_urls:
           url = client.get_qrcode(socket_url)
           gui.insert_qrcode(url)  # 插入 ASCII 二维码到日志文本中
           logging.info(f"上面二维码的地址是: {url}")
        
        await client.bind()
        logging.info(f"已与 App {client.target_id} 成功绑定")

        async for data in client.data_generator(FeedbackButton, RetCode):
            if isinstance(data, FeedbackButton):
                logging.info(f"App 触发了反馈按钮：{data.name}")

            if data == FeedbackButton.A1:
                logging.info("对方按下了 A 通道圆圈按钮，开始发送波形")
                pulse_manager.start_sending(client)

            elif data == FeedbackButton.A2:
                logging.info("对方按下了 A 通道暂停按钮，暂停发送波形")
                pulse_manager.stop_sending(client)

            elif data == RetCode.CLIENT_DISCONNECTED:
                logging.info("App 已断开连接，你可以尝试重新扫码进行连接绑定")
                pulse_manager.stop_sending(client)
                await client.rebind()
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