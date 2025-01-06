from osc_server import OSCServer
from threading import Thread
from queue import Queue, Empty
from shared_resources import normalized_queue  # 导入队列
import asyncio
import io
import qrcode

from pydglab_ws import FeedbackButton, Channel, RetCode, DGLabWSServer, StrengthOperationType
import time
import copy
import traceback

class PulseManager:
    def __init__(self):
        # 为每个通道维护独立的 lastdata 和 nextdata
        self.data = {
            Channel.A: {'lastdata': [], 'nextdata': []},
            Channel.B: {'lastdata': [], 'nextdata': []}
        }
        self.sending_task = None
        self.paused = False

    async def pulse_task(self, client):
        try:
            while not self.paused:
                try:
                    normalize = None
                    address = None

                    while not normalized_queue.empty():
                        address, normalize = normalized_queue.get_nowait()
                        normalized_queue.task_done()

                    if normalize is None:
                        await asyncio.sleep(0.02)
                        continue

                    if int(normalize) == 0:
                        continue
                    
                    if 'left' in address:
                        print(normalize)

                    # 根据 address 中的子字符串决定使用哪个通道的数据
                    channel = Channel.A if 'left' in address else Channel.B if 'right' in address else None
                    if channel:
                        channel_data = self.data[channel]
                        if len(channel_data['nextdata']) < 4:
                            channel_data['nextdata'].append(int(normalize))
                        else:
                            if len(channel_data['lastdata']) > 0:
                                print(f"Channel {channel} last: {channel_data['lastdata']}")
                                print(f"Channel {channel} next: {channel_data['nextdata']}")
                                await client.add_pulses(channel, *[((10, 10, 10, 10), channel_data['lastdata']), ((10, 10, 10, 10), channel_data['nextdata'])])
                                channel_data['lastdata'] = copy.copy(channel_data['nextdata'])
                            else:
                                channel_data['lastdata'] = copy.copy(channel_data['nextdata'])
                            channel_data['nextdata'].clear()

                    await asyncio.sleep(0.02)
                except Empty:
                    await asyncio.sleep(0.02)
                    continue
        except asyncio.CancelledError:
            print("Pulse task was cancelled.")
        finally:
            self.sending_task = None

    def start_sending(self, client):
        self.paused = False
        if self.sending_task is None or self.sending_task.done():
            self.sending_task = asyncio.create_task(self.pulse_task(client))
            print("Started sending task.")

    def stop_sending(self):
        self.paused = True
        if self.sending_task is not None:
            self.sending_task.cancel()
            self.sending_task = None
            print("Stopped sending task.")

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
        url2 = client.get_qrcode("ws://192.168.31.247:5678")
        print("请用 DG-Lab App 扫描二维码以连接")
        print_qrcode(url2)

        await client.bind()
        print(f"已与 App {client.target_id} 成功绑定")

        async for data in client.data_generator(FeedbackButton, RetCode):
            if isinstance(data, FeedbackButton):
                print(f"App 触发了反馈按钮：{data.name}")

            if data == FeedbackButton.A1:
                print("对方按下了 A 通道圆圈按钮，开始发送波形")
                pulse_manager.start_sending(client)

            elif data == FeedbackButton.A2:  # 假设 A2 是暂停按钮
                print("对方按下了 A 通道暂停按钮，暂停发送波形")
                pulse_manager.stop_sending()

            elif data == RetCode.CLIENT_DISCONNECTED:
                print("App 已断开连接，你可以尝试重新扫码进行连接绑定")
                await client.rebind()
                print("重新绑定成功")

async def main():
    ip = "127.0.0.1"
    port = 9001

    # 实例化并启动 OSC 服务器
    osc_server = OSCServer(ip, port)
    osc_server.start()

    # 启动 WebSocket 处理
    await dglab_websocket()

if __name__ == "__main__":
    asyncio.run(main())