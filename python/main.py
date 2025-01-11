import asyncio
import tkinter as tk
import threading
import logging
from config_manager import ConfigManager
from osc_server import OSCServer
from gui import AppGUI
from pulse_manager import PulseManager
from dglab_client import handle_dglab_connection
from pydglab_ws import DGLabWSServer


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config = ConfigManager()

async def main(gui):
    # 启动OSC服务器
    osc_server = OSCServer(config.osc_host, config.osc_port)
    osc_server.start()

    # 创建脉冲管理器
    pulse_manager = PulseManager()

    # 启动DGLab websocket服务器
    async with DGLabWSServer(config.host, config.port, 60) as server:
        client = server.new_local_client()
        
        # 生成二维码
        for socket_url in config.socket_urls:
            url = client.get_qrcode(socket_url)
            gui.insert_qrcode(url)
        
        # 处理DGLab连接
        await handle_dglab_connection(server, client, gui, pulse_manager)


if __name__ == "__main__":
    root = tk.Tk()
    gui = AppGUI(root)
    
    threading.Thread(target=lambda: asyncio.run(main(gui)), 
                    daemon=True).start()
    
    root.mainloop()