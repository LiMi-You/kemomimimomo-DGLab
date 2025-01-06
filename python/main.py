from osc_server import OSCServer
from threading import Thread
from queue import Queue, Empty
from shared_resources import normalized_queue
import asyncio
import io
import qrcode
import logging

from pydglab_ws import FeedbackButton, Channel, RetCode, DGLabWSServer
import time
import copy

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PulseManager:
    def __init__(self):
        self.data = {
            Channel.A: {'lastdata': [], 'nextdata': []},
            Channel.B: {'lastdata': [], 'nextdata': []}
        }
        self.sending_task = None
        self.paused = False
        self.clients = set()

    async def pulse_task(self):
        try:
            while not self.paused:
                try:
                    address, normalize = normalized_queue.get_nowait()
                    channel = Channel.A if 'left' in address else Channel.B if 'right' in address else None
                    if channel:
                        self.process_channel_data(channel, int(normalize))
                except Empty:
                    await asyncio.sleep(0.01)  # Short sleep to yield control and prevent busy waiting
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logging.info("Pulse task was cancelled.")
        finally:
            self.sending_task = None

    def process_channel_data(self, channel, normalize):
        channel_data = self.data[channel]
        if len(channel_data['nextdata']) < 4:
            channel_data['nextdata'].append(normalize)
        else:
            if len(channel_data['lastdata']) > 0:
                logging.info(f"Channel {channel} last: {channel_data['lastdata']}")
                logging.info(f"Channel {channel} next: {channel_data['nextdata']}")
                # Broadcast data to all clients
                for client in self.clients:
                    # Simulate sending data to client
                    pass
            channel_data['lastdata'] = copy.copy(channel_data['nextdata'])
            channel_data['nextdata'].clear()

    def start_sending(self):
        self.paused = False
        if self.sending_task is None or self.sending_task.done():
            self.sending_task = asyncio.create_task(self.pulse_task())
            logging.info("Started sending task.")

    def stop_sending(self):
        self.paused = True
        if self.sending_task is not None:
            self.sending_task.cancel()
            logging.info("Stopped sending task.")

    def add_client(self, client):
        self.clients.add(client)
        logging.info(f"Client {client} added.")

    def remove_client(self, client):
        self.clients.discard(client)
        logging.info(f"Client {client} removed.")

def print_qrcode(data: str):
    qr = qrcode.QRCode()
    qr.add_data(data)
    qr.make(fit=True)
    f = io.StringIO()
    qr.print_ascii(out=f, invert=True)
    f.seek(0)
    print(f.read())

async def dglab_websocket():
    pulse_manager = PulseManager()
    async with DGLabWSServer("0.0.0.0", 5678, 60) as server:
        client = server.new_local_client()
        pulse_manager.add_client(client)
        url2 = client.get_qrcode("ws://192.168.31.247:5678")
        logging.info("请用 DG-Lab App 扫描二维码以连接")
        print_qrcode(url2)

        await client.bind()
        logging.info(f"已与 App {client.target_id} 成功绑定")

        async for data in client.data_generator(FeedbackButton, RetCode):
            if isinstance(data, FeedbackButton):
                logging.info(f"App 触发了反馈按钮：{data.name}")

            if data == FeedbackButton.A1:
                logging.info("对方按下了 A 通道圆圈按钮，开始发送波形")
                pulse_manager.start_sending()

            elif data == FeedbackButton.A2:
                logging.info("对方按下了 A 通道暂停按钮，暂停发送波形")
                pulse_manager.stop_sending()

            elif data == RetCode.CLIENT_DISCONNECTED:
                logging.info("App 已断开连接，你可以尝试重新扫码进行连接绑定")
                pulse_manager.remove_client(client)
                await client.rebind()
                pulse_manager.add_client(client)
                logging.info("重新绑定成功")

async def main():
    ip = "127.0.0.1"
    port = 9001

    osc_server = OSCServer(ip, port)
    osc_server.start()

    await dglab_websocket()

if __name__ == "__main__":
    asyncio.run(main())