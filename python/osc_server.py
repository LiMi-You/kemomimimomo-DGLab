from pythonosc import dispatcher, osc_server
from threading import Thread, Lock
from time import time
from collections import deque
from shared_resources import normalized_queue  # 导入队列
import asyncio

class OSCServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.data_store = {}
        self.acceleration_window = {}
        self.lock = Lock()

    def normalize_and_map(self, x):
        min_original = 10
        max_original = 450
        min_new = 0
        max_new = 100

        x = max(min(x, max_original), min_original)
        y = ((x - min_original) / (max_original - min_original)) * (max_new - min_new) + min_new
        return y

    def print_handler(self, address, *args):
        address = address.replace("$", "")
        current_value = args[0]
        current_time = time()

        with self.lock:
            self.data_store.setdefault(address, []).append((current_value, current_time))
            if len(self.data_store[address]) > 2:
                self.data_store[address].pop(0)

    async def sample_data(self):
        while True:
            current_time = time()
            addresses_to_remove = []

            for address, values in self.data_store.items():
                if not values:
                    continue

                last_value, last_time = values[-1] if values else (None, None)

                if last_time is None or current_time - last_time > 0.025:
                    current_value = 0
                    acceleration_abs = 0
                else:
                    current_value = last_value

                    if len(values) == 2:
                        prev_value, prev_time = values[0]
                        delta_t = current_time - prev_time

                        if delta_t != 0:
                            velocity_change = (current_value - prev_value) / delta_t
                            acceleration = velocity_change / delta_t if delta_t != 0 else 0
                            acceleration_abs = abs(acceleration)
                        else:
                            acceleration_abs = 0
                    else:
                        acceleration_abs = 0

                with self.lock:
                    if address not in self.acceleration_window:
                        self.acceleration_window[address] = deque(maxlen=5)
                    self.acceleration_window[address].append(acceleration_abs)

                    filtered_acceleration = sum(self.acceleration_window[address]) / len(self.acceleration_window[address])
                    normalize = self.normalize_and_map(filtered_acceleration)
                    normalized_queue.put((address, normalize))

                if len(values) > 1 and current_time - values[0][1] > 0.025:
                    self.data_store[address].pop(0)

            await asyncio.sleep(0.025)

    def start(self):
        disp = dispatcher.Dispatcher()
        disp.map("/avatar/parameters/ear_touch_*", self.print_handler)

        server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), disp)
        print(f"Serving on {server.server_address}")

        loop = asyncio.get_event_loop()
        loop.create_task(self.sample_data())
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

def start_osc_server(ip, port):
    osc_server = OSCServer(ip, port)
    osc_server.start()