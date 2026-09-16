"""
Sends synthetic AoA CSV packets over UDP to localhost:5005 for testing the
visualization without real hardware. Azimuth sweeps 0-360 deg while
elevation oscillates -30..+30 deg.

Usage: python test_sender.py [host] [port]
"""

import math
import socket
import sys
import time

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

t = 0.0
try:
    while True:
        azimuth = (t * 20) % 360
        elevation = 30 * math.sin(t * 0.5)
        timestamp = time.time()
        line = f"{timestamp:.6f},{azimuth:.2f},{elevation:.2f}"
        sock.sendto(line.encode("utf-8"), (host, port))
        print("sent:", line)
        t += 0.2
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
