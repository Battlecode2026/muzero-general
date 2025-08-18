"""
PokerGame implementation of AbstractGame interface for MuZero training.
Interfaces with MIT Pokerbots Engine via PokerSocket communication layer.
"""

import numpy as np
from typing import List, Tuple, Optional
from .abstract_game import AbstractGame
from .poker_socket import PokerSocket


class PokerGame(AbstractGame):
    """MuZero game interface for poker using MIT Pokerbots Engine."""
    
    def __init__(self, seed: Optional[int] = None, training_mode: bool = True):
        self.training_mode = training_mode
        self.seed = seed
        
        # Training vs competition timeouts
        config_overrides = {}
        if training_mode:
            config_overrides = {
                'STARTING_GAME_CLOCK': 600.0,  # 10 minutes for training
                'PLAYER_TIMEOUT': 300,         # 5 minutes per action
                'ENFORCE_GAME_CLOCK': 'False'  # Disable for initial training
            }
        
        self.poker_socket = PokerSocket(config_overrides=config_overrides)
        self.current_observation = None
        self.game_over = False
        self.last_reward = 0.0
        
        # Action space: 0=fold, 1=call, 2=check, 3-102=raise amounts
        self.action_space_size = 103
        self.min_raise = 2  # Big blind
        self.max_raise = 400  # Starting stack
        
        # Initialize random state if seed provided
        if seed is not None:
            np.random.seed(seed)
    
    def _encode_observation(self, message: dict) -> np.ndarray:
        """Convert poker socket message to MuZero observation vector."""
        # Create observation vector (~200 dimensions)
        obs = np.zeros(200, dtype=np.float32)
        
        if not message:
            return obs
            
        # Time remaining (normalized to 0-1)
        if message.get('time_remaining'):
            obs[0] = min(message['time_remaining'] / 600.0, 1.0)
        
        # Player index
        if message.get('player_index') is not None:
            obs[1] = message['player_index']
        
        # Hole cards (52 binary features for each card)
        hole_cards = message.get('hole_cards', [])
        for i, card in enumerate(hole_cards[:2]):
            if card:
                card_idx = self._card_to_index(card)
                if card_idx >= 0:
                    obs[2 + card_idx] = 1.0
        
        # Board cards (52 binary features)
        board_cards = message.get('board_cards', [])
        for card in board_cards[:5]:
            if card:
                card_idx = self._card_to_index(card)
                if card_idx >= 0:
                    obs[54 + card_idx] = 1.0
        
        # Action history encoding (last 10 actions)
        action_history = message.get('action_history', [])
        for i, action in enumerate(action_history[-10:]):
            if action == 'F':
                obs[106 + i*4] = 1.0
            elif action == 'C':
                obs[107 + i*4] = 1.0
            elif action == 'K':
                obs[108 + i*4] = 1.0
            elif action.startswith('R'):
                obs[109 + i*4] = min(int(action[1:]) / 400.0, 1.0)
        
        # Bankroll delta (normalized)
        if message.get('bankroll_delta') is not None:
            obs[146] = message['bankroll_delta'] / 400.0
            
        return obs
    
    def _card_to_index(self, card_str: str) -> int:
        """Convert card string (e.g., 'As', 'Kh') to index 0-51."""
        if len(card_str) != 2:
            return -1
        
        ranks = '23456789TJQKA'
        suits = 'shdc'  # spades, hearts, diamonds, clubs
        
        try:
            rank_idx = ranks.index(card_str[0])
            suit_idx = suits.index(card_str[1])
            return rank_idx * 4 + suit_idx
        except ValueError:
            return -1
    
    def _action_to_poker_code(self, action: int) -> str:
        """Convert MuZero action index to poker protocol string."""
        if action == 0:
            return 'F'  # Fold
        elif action == 1:
            return 'C'  # Call
        elif action == 2:
            return 'K'  # Check
        elif 3 <= action <= 102:
            # Raise actions: map to amounts 2-400
            raise_amount = self.min_raise + ((action - 3) * (self.max_raise - self.min_raise) // 99)
            return f'R{raise_amount}'
        else:
            return 'K'  # Default to check for invalid actions
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        """Apply action and return (observation, reward, done)."""
        if self.game_over:
            return self.current_observation, 0.0, True
        
        # Convert action to poker protocol
        action_code = self._action_to_poker_code(action)
        
        # Send action to engine
        if not self.poker_socket.send_action(action_code):
            self.game_over = True
            return self.current_observation, -1.0, True  # Penalty for connection failure
        
        # Receive response
        message = self.poker_socket.receive_message()
        if not message:
            self.game_over = True
            return self.current_observation, -1.0, True
        
        # Update state
        self.current_observation = self._encode_observation(message)
        self.game_over = message.get('game_over', False)
        
        # Calculate reward
        reward = 0.0
        if message.get('bankroll_delta') is not None:
            reward = message['bankroll_delta'] / 400.0  # Normalize by starting stack
        
        return self.current_observation, reward, self.game_over
    
    def legal_actions(self) -> List[int]:
        """Return legal actions for current state."""
        # For now, return all actions - engine will handle illegal action filtering
        # TODO: Parse game state to determine actual legal actions
        return list(range(self.action_space_size))
    
    def reset(self) -> np.ndarray:
        """Reset game and return initial observation."""
        # Close existing connection
        if self.poker_socket.is_connected():
            self.poker_socket.close()
        
        # Start new game
        if not self.poker_socket.start_engine():
            raise RuntimeError("Failed to start poker engine")
        
        # Wait for initial message
        time.sleep(1)
        message = self.poker_socket.receive_message()
        
        self.current_observation = self._encode_observation(message)
        self.game_over = False
        self.last_reward = 0.0
        
        return self.current_observation
    
    def render(self) -> None:
        """Display current game state."""
        if self.current_observation is not None:
            print(f"Poker Game State (observation shape: {self.current_observation.shape})")
            print(f"Time remaining: {self.current_observation[0]:.3f}")
            print(f"Player index: {int(self.current_observation[1])}")
            print(f"Game over: {self.game_over}")
        else:
            print("No current observation")
    
    def close(self) -> None:
        """Clean up resources."""
        if self.poker_socket:
            self.poker_socket.close()
    
    def to_play(self) -> int:
        """Return current player (always 0 for our MuZero agent)."""
        return 0
    
    def action_to_string(self, action_number: int) -> str:
        """Convert action number to readable string."""
        if action_number == 0:
            return "Fold"
        elif action_number == 1:
            return "Call"
        elif action_number == 2:
            return "Check"
        elif 3 <= action_number <= 102:
            raise_amount = self.min_raise + ((action_number - 3) * (self.max_raise - self.min_raise) // 99)
            return f"Raise {raise_amount}"
        else:
            return f"Unknown action {action_number}"