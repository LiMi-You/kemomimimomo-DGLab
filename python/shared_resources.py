# shared_resources.py
from queue import Queue

# 初始化线程安全的队列，并导出供其他模块使用
normalized_queue = Queue(maxsize=1000)