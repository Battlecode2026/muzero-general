"""
Engine process lifecycle management for poker training.
Handles subprocess creation, configuration, and cleanup between episodes.
"""

import os
import subprocess
import time
import tempfile
import shutil
from typing import Dict, Optional, List
from pathlib import Path


class PokerEngineManager:
    """Manages poker engine processes for MuZero training."""
    
    def __init__(self, engine_path: str = "../engine-2025"):
        self.engine_path = os.path.abspath(engine_path)
        self.current_process = None
        self.training_dir = None
        self.config_file = None
        
    def create_training_environment(self, config_overrides: Optional[Dict] = None) -> str:
        """Create isolated training directory with custom config."""
        # Create temporary training directory
        self.training_dir = tempfile.mkdtemp(prefix="poker_training_")
        
        # Copy engine files to training directory
        engine_files = [
            "engine.py",
            "python_skeleton",
            "cpp_skeleton", 
            "java_skeleton"
        ]
        
        for file_name in engine_files:
            src_path = os.path.join(self.engine_path, file_name)
            dst_path = os.path.join(self.training_dir, file_name)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
        
        # Create training-specific config
        self.config_file = self._create_training_config(config_overrides or {})
        
        return self.training_dir
    
    def _create_training_config(self, overrides: Dict) -> str:
        """Generate config.py for training with appropriate settings."""
        # Default training settings
        default_config = {
            'PLAYER_1_NAME': '"MuZero"',
            'PLAYER_1_PATH': '"./muzero_bot"',
            'PLAYER_2_NAME': '"RandomBot"', 
            'PLAYER_2_PATH': '"./python_skeleton"',
            'GAME_LOG_FILENAME': '"muzero_training"',
            'PLAYER_LOG_SIZE_LIMIT': 1048576,  # 1MB
            'ENFORCE_GAME_CLOCK': False,  # Disable for training
            'STARTING_GAME_CLOCK': 3600.0,  # 1 hour for training
            'BUILD_TIMEOUT': 30.0,
            'CONNECT_TIMEOUT': 30.0,
            'NUM_ROUNDS': 100,  # Shorter games for training
            'STARTING_STACK': 400,
            'BIG_BLIND': 2,
            'SMALL_BLIND': 1,
            'ROUNDS_PER_BOUNTY': 25,
            'BOUNTY_RATIO': 1.5,
            'BOUNTY_CONSTANT': 10,
            'PLAYER_TIMEOUT': 300  # 5 minutes per action
        }\n        \n        # Apply overrides\n        final_config = {**default_config, **overrides}\n        \n        # Generate config file content\n        config_content = \"# Training configuration for MuZero poker integration\\n\"\n        config_content += \"# Auto-generated - do not edit manually\\n\\n\"\n        \n        for key, value in final_config.items():\n            if isinstance(value, str) and not value.startswith('\"'):\n                value = f'\"{value}\"'\n            config_content += f\"{key} = {value}\\n\"\n        \n        # Write config file\n        config_path = os.path.join(self.training_dir, \"config.py\")\n        with open(config_path, 'w') as f:\n            f.write(config_content)\n            \n        return config_path\n    \n    def create_muzero_bot_stub(self) -> str:\n        \"\"\"Create a placeholder bot that MuZero will control via socket.\"\"\"\n        bot_dir = os.path.join(self.training_dir, \"muzero_bot\")\n        os.makedirs(bot_dir, exist_ok=True)\n        \n        # Create commands.json\n        commands = {\n            \"build\": [],\n            \"run\": [\"python3\", \"player.py\"]\n        }\n        \n        with open(os.path.join(bot_dir, \"commands.json\"), 'w') as f:\n            import json\n            json.dump(commands, f, indent=2)\n        \n        # Create player.py stub that connects back to MuZero\n        player_code = '''#!/usr/bin/env python3\n\"\"\"MuZero-controlled poker bot stub.\"\"\"\nimport sys\nimport socket\n\ndef main():\n    if len(sys.argv) != 2:\n        print(\"Usage: python player.py <port>\")\n        sys.exit(1)\n    \n    port = int(sys.argv[1])\n    \n    # Connect back to MuZero process\n    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n    sock.connect((\"localhost\", port))\n    socketfile = sock.makefile(\"rw\")\n    \n    try:\n        while True:\n            # Read message from engine\n            line = socketfile.readline().strip()\n            if not line:\n                break\n                \n            # Forward to MuZero (this will be replaced by actual communication)\n            # For now, just send check/call actions\n            if \"T\" in line:  # Time message, need to respond\n                socketfile.write(\"K\\\\n\")  # Send check\n                socketfile.flush()\n                \n    except Exception as e:\n        print(f\"Bot error: {e}\")\n    finally:\n        socketfile.close()\n        sock.close()\n\nif __name__ == \"__main__\":\n    main()\n'''\n        \n        with open(os.path.join(bot_dir, \"player.py\"), 'w') as f:\n            f.write(player_code)\n            \n        # Make executable\n        os.chmod(os.path.join(bot_dir, \"player.py\"), 0o755)\n        \n        return bot_dir\n    \n    def start_engine(self, config_overrides: Optional[Dict] = None) -> bool:\n        \"\"\"Start poker engine process with training configuration.\"\"\"\n        try:\n            # Set up training environment\n            self.create_training_environment(config_overrides)\n            self.create_muzero_bot_stub()\n            \n            # Start engine process\n            engine_script = os.path.join(self.training_dir, \"engine.py\")\n            \n            # Ensure engine can find our config\n            env = os.environ.copy()\n            env['PYTHONPATH'] = self.training_dir\n            \n            self.current_process = subprocess.Popen(\n                [\"python3\", engine_script],\n                cwd=self.training_dir,\n                env=env,\n                stdout=subprocess.PIPE,\n                stderr=subprocess.PIPE,\n                text=True\n            )\n            \n            # Give engine time to initialize\n            time.sleep(2)\n            \n            # Check if process started successfully\n            if self.current_process.poll() is None:\n                return True\n            else:\n                stdout, stderr = self.current_process.communicate()\n                print(f\"Engine failed to start: {stderr}\")\n                return False\n                \n        except Exception as e:\n            print(f\"Failed to start engine: {e}\")\n            return False\n    \n    def stop_engine(self) -> None:\n        \"\"\"Stop current engine process and clean up.\"\"\"\n        if self.current_process:\n            self.current_process.terminate()\n            try:\n                self.current_process.wait(timeout=5)\n            except subprocess.TimeoutExpired:\n                self.current_process.kill()\n                self.current_process.wait()\n            self.current_process = None\n    \n    def restart_engine(self, config_overrides: Optional[Dict] = None) -> bool:\n        \"\"\"Restart engine with new configuration.\"\"\"\n        self.stop_engine()\n        self.cleanup_training_dir()\n        return self.start_engine(config_overrides)\n    \n    def cleanup_training_dir(self) -> None:\n        \"\"\"Remove temporary training directory.\"\"\"\n        if self.training_dir and os.path.exists(self.training_dir):\n            shutil.rmtree(self.training_dir)\n            self.training_dir = None\n            self.config_file = None\n    \n    def is_engine_running(self) -> bool:\n        \"\"\"Check if engine process is still running.\"\"\"\n        return self.current_process is not None and self.current_process.poll() is None\n    \n    def get_engine_output(self) -> tuple:\n        \"\"\"Get current stdout/stderr from engine process.\"\"\"\n        if not self.current_process:\n            return \"\", \"\"\n            \n        try:\n            stdout, stderr = self.current_process.communicate(timeout=0.1)\n            return stdout, stderr\n        except subprocess.TimeoutExpired:\n            return \"\", \"\"  # No new output\n    \n    def __del__(self):\n        \"\"\"Cleanup on destruction.\"\"\"\n        self.stop_engine()\n        self.cleanup_training_dir()