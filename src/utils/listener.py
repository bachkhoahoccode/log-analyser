import asyncio
import os

class LogListener:
    def __init__(self, file_configs, parser_queue):

        self.file_configs = file_configs
        self.queue = parser_queue
        # Track the last read position (byte offset) for each file
        self.file_positions = {} 
        self.is_running = True
        self.formats = [config["format"] for config in file_configs]

    async def start_live_listening(self):
        print("[Listener] 🎬 Live tracking started for configured files...")
        
        for config in self.file_configs:
            path = config["log_file_path"]
            if os.path.exists(path):
                self.file_positions[path] = os.path.getsize(path)
            else:
                self.file_positions[path] = 0

        # The 1-second check loop
        while self.is_running:
            for config in self.file_configs:
                path = config["log_file_path"]
                file_format = config.get("format", "unknown")        
                if not os.path.exists(path):
                    continue
                
                current_size = os.path.getsize(path)
                last_position = self.file_positions.get(path, 0)
                
                # Check if file has grown
                if current_size > last_position:
                    await self._read_latest_bit(path, last_position, file_format)
                    self.file_positions[path] = current_size # Update pointer
            await asyncio.sleep(1)

    async def _read_latest_bit(self, path, start_bytes, file_format):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(start_bytes)
            new_lines = f.readlines()
            for line in new_lines:
                clean_line = line.strip()
                if clean_line:
                    # format metadata
                    payload = {
                        "raw_line": clean_line,
                        "format": file_format,
                    }
                    await self.queue.put(payload)