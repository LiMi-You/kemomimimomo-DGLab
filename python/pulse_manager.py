import asyncio
import logging
import copy
from queue import Empty
from pydglab_ws import Channel
from shared_resources import normalized_queue

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
