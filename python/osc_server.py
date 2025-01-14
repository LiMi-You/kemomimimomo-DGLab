from pythonosc import dispatcher, osc_server
from threading import Thread
import asyncio
import logging
from time import time
from collections import deque
from shared_resources import normalized_queue
from config_manager import ConfigManager
import math
config = ConfigManager()
class OSCServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.data_store = {}
        self.acceleration_window = {}
        self.server_thread = None

    def normalize_and_map(self, x):
        min_original = config.min_original
        max_original = config.max_original
        min_new = 0
        max_new = 100

        x = max(min(x, max_original), min_original)
        y = ((x - min_original) / (max_original - min_original)) * (max_new - min_new) + min_new
        return y

    def normalize_and_map(self, x,min_original,max_original,min_new,max_new):
        x = max(min(x, max_original), min_original)
        y = ((x - min_original) / (max_original - min_original)) * (max_new - min_new) + min_new
        return y
    
    def frequency(self,x,min_original,max_original):
        frequency_constant_p = config.frequency_constant_p
        frequency_constant_a = config.frequency_constant_a
        frequency_constant_b = config.frequency_constant_b

        y = self.normalize_and_map(x,min_original,max_original,0,100)

           # 首先检查2px - b^2是否非负，因为不能对负数开平方
        under_sqrt = 2 * frequency_constant_p * y - frequency_constant_b**2
        if under_sqrt < 0:
            return "Error: Cannot take the square root of a negative number."
        
        y = frequency_constant_a + math.sqrt(under_sqrt)
        return int(1000/self.normalize_and_map(x,0,100,1,500))

        



    def print_handler(self, address, *args):
        address = address.replace("$", "")
        current_value = args[0]
        current_time = time()

        # Store the latest value and time
        self.data_store[address] = (current_value, current_time)

        # Calculate acceleration if possible
        if address in self.acceleration_window and len(self.acceleration_window[address]) >= 1:
            prev_value, prev_time = self.acceleration_window[address][-1]
            delta_t = current_time - prev_time
            if delta_t > 0:
                acceleration = (current_value - prev_value) / delta_t
                normalized_value = self.normalize_and_map(abs(acceleration),config.min_original,config.max_original,0,100)
                frequency_value = self.frequency(abs(acceleration),config.min_original,config.max_original)
                # print(abs(acceleration))
                normalized_queue.put((address, (normalized_value,frequency_value)))
        else:
            # Initialize deque for new addresses
            self.acceleration_window[address] = deque(maxlen=2)

        # Update the acceleration window
        self.acceleration_window[address].append((current_value, current_time))

    def start(self):
        disp = dispatcher.Dispatcher()
        disp.map("/avatar/parameters/ear_touch_*", self.print_handler)

        server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), disp)
        logging.info(f"Serving on {server.server_address}")

        self.server_thread = Thread(target=server.serve_forever, daemon=True)
        self.server_thread.start()

    def stop(self):
        if self.server_thread:
            self.server_thread.join()
            logging.info("OSC server stopped.")

def start_osc_server(ip, port):
    osc_server = OSCServer(ip, port)
    osc_server.start()