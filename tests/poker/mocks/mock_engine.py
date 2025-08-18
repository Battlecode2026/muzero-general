"""
Mock poker engine for testing PokerSocket and PokerGame without subprocess overhead.
Simulates engine socket behavior with deterministic responses.
"""

import socket
import threading
import time
from typing import List, Dict, Optional


class MockPokerEngine:
    """Mock poker engine that simulates socket communication."""
    
    def __init__(self, port: int = 12345):
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.thread = None
        self.message_queue = []
        self.responses = []
        
    def add_response(self, message: str) -> None:
        """Add a pre-canned response message."""
        self.responses.append(message)
    
    def start(self) -> bool:
        """Start the mock engine server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(1)
            self.running = True
            
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"Mock engine start failed: {e}")
            return False
    
    def _run_server(self) -> None:
        """Main server loop."""
        try:
            self.client_socket, _ = self.server_socket.accept()
            socketfile = self.client_socket.makefile('rw')
            
            response_idx = 0
            while self.running and response_idx < len(self.responses):
                # Send next response
                if response_idx < len(self.responses):
                    socketfile.write(self.responses[response_idx] + '\n')
                    socketfile.flush()
                    response_idx += 1
                
                # Read client action
                try:
                    action = socketfile.readline().strip()
                    if action:
                        self.message_queue.append(action)
                except socket.timeout:
                    pass
                
                time.sleep(0.1)  # Small delay to simulate real engine
                
        except Exception as e:
            print(f"Mock engine error: {e}")
        finally:
            if self.client_socket:
                self.client_socket.close()
    
    def stop(self) -> None:
        """Stop the mock engine."""
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        if self.thread:
            self.thread.join(timeout=1)
    
    def get_received_actions(self) -> List[str]:
        """Get actions received from client."""
        actions = list(self.message_queue)
        self.message_queue.clear()
        return actions


class MockPokerScenarios:
    """Pre-defined poker scenarios for testing."""
    
    @staticmethod
    def simple_hand() -> List[str]:
        """Simple hand scenario with fold action."""
        return [
            "T600.000 P0 H2s,3h",  # Initial hand
            "T599.500 P0 H2s,3h BActs F",  # After opponent folds
            "D2 Q"  # Game over, won 2 chips
        ]
    
    @staticmethod
    def full_hand() -> List[str]:
        """Full hand with multiple betting rounds."""
        return [
            "T600.000 P0 H7s,8s",  # Hole cards
            "T599.800 P0 H7s,8s BActs C",  # After call
            "T599.600 P0 H7s,8s B9h,Td,Jc BActs C",  # Flop
            "T599.400 P0 H7s,8s B9h,Td,Jc,Qs BActs C",  # Turn  
            "T599.200 P0 H7s,8s B9h,Td,Jc,Qs,Ah BActs C",  # River
            "O2c,2d D-50 Q"  # Showdown, lost 50 chips
        ]
    
    @staticmethod
    def timeout_scenario() -> List[str]:
        """Scenario that tests timeout handling."""
        return [
            "T5.000 P0 HAh,As",  # Low time remaining
            "T2.000 P0 HAh,As BActs R10",  # Very low time
            "D0 Q"  # Timeout/fold
        ]