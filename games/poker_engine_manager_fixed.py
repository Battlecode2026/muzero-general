"""
Engine process lifecycle management for poker training.
Handles subprocess creation, configuration, and cleanup between episodes.
"""

import os
import subprocess
import time
import tempfile
import shutil
import json
from typing import Dict, Optional


class PokerEngineManager:
    """Manages poker engine processes for MuZero training."""
    
    def __init__(self, engine_path: str = "../engine-2025"):
        self.engine_path = os.path.abspath(engine_path)
        self.current_process = None
        self.training_dir = None
        self.config_file = None
        
    def create_training_environment(self, config_overrides: Optional[Dict] = None) -> str:
        """Create isolated training directory with custom config."""
        self.training_dir = tempfile.mkdtemp(prefix="poker_training_")
        
        # Copy essential engine files
        engine_files = ["engine.py", "python_skeleton"]
        
        for file_name in engine_files:
            src_path = os.path.join(self.engine_path, file_name)
            dst_path = os.path.join(self.training_dir, file_name)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
        
        # Create training config
        self.config_file = self._create_training_config(config_overrides or {})
        
        return self.training_dir
    
    def _create_training_config(self, overrides: Dict) -> str:
        """Generate config.py for training."""
        default_config = {
            'PLAYER_1_NAME': '"MuZero"',
            'PLAYER_1_PATH': '"./muzero_bot"',
            'PLAYER_2_NAME': '"RandomBot"', 
            'PLAYER_2_PATH': '"./python_skeleton"',
            'GAME_LOG_FILENAME': '"muzero_training"',
            'PLAYER_LOG_SIZE_LIMIT': 1048576,
            'ENFORCE_GAME_CLOCK': False,
            'STARTING_GAME_CLOCK': 3600.0,
            'BUILD_TIMEOUT': 30.0,
            'CONNECT_TIMEOUT': 30.0,
            'NUM_ROUNDS': 100,
            'STARTING_STACK': 400,
            'BIG_BLIND': 2,
            'SMALL_BLIND': 1,
            'ROUNDS_PER_BOUNTY': 25,
            'BOUNTY_RATIO': 1.5,
            'BOUNTY_CONSTANT': 10,
            'PLAYER_TIMEOUT': 300
        }
        
        # Apply overrides
        final_config = {**default_config, **overrides}
        
        # Generate config content
        lines = []
        lines.append("# Training configuration for MuZero poker integration")
        lines.append("# Auto-generated - do not edit manually")
        lines.append("")
        
        for key, value in final_config.items():
            if isinstance(value, str) and not value.startswith('"'):
                value = f'"{value}"'
            lines.append(f"{key} = {value}")
        
        config_content = "\\n".join(lines)
        
        # Write config file
        config_path = os.path.join(self.training_dir, "config.py")
        with open(config_path, 'w') as f:
            f.write(config_content)
            
        return config_path
    
    def create_muzero_bot_stub(self) -> str:
        """Create placeholder bot directory."""
        bot_dir = os.path.join(self.training_dir, "muzero_bot")
        os.makedirs(bot_dir, exist_ok=True)
        
        # Create commands.json
        commands = {
            "build": [],
            "run": ["python3", "player.py"]
        }
        
        with open(os.path.join(bot_dir, "commands.json"), 'w') as f:
            json.dump(commands, f, indent=2)
        
        # Create simple player.py stub
        player_code = """#!/usr/bin/env python3
import sys
import socket

def main():
    if len(sys.argv) != 2:
        print("Usage: python player.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", port))
    socketfile = sock.makefile("rw")
    
    try:
        while True:
            line = socketfile.readline().strip()
            if not line:
                break
            if "T" in line:
                socketfile.write("K\\n")
                socketfile.flush()
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        socketfile.close()
        sock.close()

if __name__ == "__main__":
    main()
"""
        
        with open(os.path.join(bot_dir, "player.py"), 'w') as f:
            f.write(player_code)
            
        os.chmod(os.path.join(bot_dir, "player.py"), 0o755)
        return bot_dir
    
    def cleanup_training_dir(self) -> None:
        """Remove temporary training directory."""
        if self.training_dir and os.path.exists(self.training_dir):
            shutil.rmtree(self.training_dir)
            self.training_dir = None
            self.config_file = None