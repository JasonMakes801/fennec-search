"""
Simple progress indicators for long-running operations.
Docker logs don't handle carriage returns well, so we use
periodic newline-based updates instead.
"""

import sys
import threading
import time


class Spinner:
    """Simple spinner that prints dots periodically."""
    
    def __init__(self, message):
        self.message = message
        self.running = False
        self.thread = None
    
    def _spin(self):
        print(f"    ⏳ {self.message}...", flush=True)
        dots = 0
        while self.running:
            time.sleep(5)  # Print a dot every 5 seconds
            if self.running:
                dots += 1
                print(f"       ...still working ({dots * 5}s)", flush=True)
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()
    
    def stop(self, final_message=None):
        self.running = False
        if self.thread:
            self.thread.join()
        if final_message:
            print(f"    ✓ {final_message}", flush=True)
        else:
            print(f"    ✓ {self.message} - done", flush=True)


def progress_counter(current, total, message, every=10):
    """
    Show progress counter every N items.
    Prints: [10/155] Message, [20/155] Message, etc.
    """
    if current == 1 or current == total or current % every == 0:
        print(f"    [{current}/{total}] {message}", flush=True)


def progress_done(message):
    """Show completion message."""
    print(f"    ✓ {message}", flush=True)
