"""
Socket communication layer for interfacing MuZero with MIT Pokerbots Engine.
Handles subprocess management, socket I/O, and message parsing.
"""

import socket
import subprocess
import os
import time
import json
from typing import Optional, Dict, List, Any
from threading import Thread
from queue import Queue


class PokerSocket:
    """Manages communication with the poker engine via subprocess and socket."""
    
    def __init__(self, engine_path: str = "../engine-2025", config_overrides: Optional[Dict] = None):
        self.engine_path = os.path.abspath(engine_path)
        self.config_overrides = config_overrides or {}
        self.engine_process = None
        self.socket_connection = None
        self.socketfile = None
        self.is_connected_flag = False
        self.stdout_queue = Queue()
        
    def _create_training_config(self) -> str:
        """Create a temporary config file with training-specific settings."""
        config_content = f"""# Training configuration for MuZero integration
PLAYER_1_NAME = "MuZero"
PLAYER_1_PATH = "./muzero_bot"
PLAYER_2_NAME = "Opponent" 
PLAYER_2_PATH = "./python_skeleton"
GAME_LOG_FILENAME = "muzero_training_log"
PLAYER_LOG_SIZE_LIMIT = 524288
ENFORCE_GAME_CLOCK = {self.config_overrides.get('ENFORCE_GAME_CLOCK', 'True')}
STARTING_GAME_CLOCK = {self.config_overrides.get('STARTING_GAME_CLOCK', 600.0)}
BUILD_TIMEOUT = 10.0
CONNECT_TIMEOUT = 10.0
NUM_ROUNDS = {self.config_overrides.get('NUM_ROUNDS', 1000)}
STARTING_STACK = 400
BIG_BLIND = 2
SMALL_BLIND = 1
ROUNDS_PER_BOUNTY = 25
BOUNTY_RATIO = 1.5
BOUNTY_CONSTANT = 10
PLAYER_TIMEOUT = {self.config_overrides.get('PLAYER_TIMEOUT', 120)}
"""
        config_path = os.path.join(self.engine_path, "training_config.py")
        with open(config_path, 'w') as f:
            f.write(config_content)
        return config_path
        
    def start_engine(self) -> bool:
        """Start the poker engine subprocess with training configuration."""
        try:
            # Create training config
            config_path = self._create_training_config()
            
            # Start engine process
            engine_script = os.path.join(self.engine_path, "engine.py")
            cmd = ["python3", engine_script]
            
            # Set PYTHONPATH to find the training config
            env = os.environ.copy()
            env['PYTHONPATH'] = self.engine_path
            
            self.engine_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.engine_path,
                env=env
            )
            
            # Start thread to capture stdout
            def capture_output():
                if self.engine_process and self.engine_process.stdout:
                    for line in iter(self.engine_process.stdout.readline, b''):
                        self.stdout_queue.put(line.decode().strip())
                        
            Thread(target=capture_output, daemon=True).start()
            
            # Give engine time to start
            time.sleep(2)
            return self.engine_process.poll() is None
            
        except Exception as e:
            print(f"Failed to start engine: {e}")
            return False
    
    def connect(self, port: int = 12345) -> bool:
        """Establish socket connection with the engine."""
        try:
            self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_connection.settimeout(10.0)
            self.socket_connection.connect(('localhost', port))
            self.socketfile = self.socket_connection.makefile('rw')
            self.is_connected_flag = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def receive_message(self) -> Optional[Dict[str, Any]]:
        """Parse incoming socket message into structured format."""
        if not self.socketfile:
            return None
            
        try:
            line = self.socketfile.readline().strip()
            if not line:
                return None
                
            clauses = line.split(' ')
            message = {
                'time_remaining': None,
                'player_index': None,
                'hole_cards': [],
                'board_cards': [],
                'action_history': [],
                'bankroll_delta': None,
                'bounty_hits': None,
                'game_over': False,
                'opponent_hand': []
            }
            
            for clause in clauses:
                if not clause:
                    continue
                    
                if clause.startswith('T'):
                    message['time_remaining'] = float(clause[1:])
                elif clause.startswith('P'):
                    message['player_index'] = int(clause[1:])
                elif clause.startswith('H'):
                    cards = clause[1:].split(',') if len(clause) > 1 else []
                    message['hole_cards'] = [c for c in cards if c]
                elif clause.startswith('B'):
                    cards = clause[1:].split(',') if len(clause) > 1 else []
                    message['board_cards'] = [c for c in cards if c]
                elif clause.startswith('O'):
                    cards = clause[1:].split(',') if len(clause) > 1 else []
                    message['opponent_hand'] = [c for c in cards if c]
                elif clause.startswith('D'):
                    message['bankroll_delta'] = int(clause[1:])
                elif clause.startswith('Y'):
                    message['bounty_hits'] = clause[1:]
                elif clause == 'Q':
                    message['game_over'] = True
                elif clause in ['F', 'C', 'K'] or clause.startswith('R'):
                    message['action_history'].append(clause)
                    
            return message
            
        except Exception as e:
            print(f"Message parsing failed: {e}")
            return None
    
    def send_action(self, action_code: str) -> bool:
        """Send action to engine in poker protocol format."""
        if not self.socketfile:
            return False
            
        try:
            self.socketfile.write(action_code + '\n')
            self.socketfile.flush()
            return True
        except Exception as e:
            print(f"Action send failed: {e}")
            return False
    
    def close(self) -> None:
        """Clean up socket connection and engine process."""
        if self.socketfile:
            self.socketfile.close()
        if self.socket_connection:
            self.socket_connection.close()
        if self.engine_process:
            self.engine_process.terminate()
            self.engine_process.wait(timeout=5)
        self.is_connected_flag = False
    
    def is_connected(self) -> bool:
        """Check if socket connection is active."""
        return self.is_connected_flag and self.socket_connection is not None
    
    def get_stdout_lines(self) -> List[str]:
        """Get captured stdout lines from engine."""
        lines = []
        while not self.stdout_queue.empty():
            lines.append(self.stdout_queue.get())
        return lines