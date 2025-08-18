"""
PokerGame implementation of AbstractGame interface for MuZero training.
Interfaces with MIT Pokerbots Engine via PokerSocket communication layer.
"""

import numpy as np
from typing import List, Tuple, Optional
from .abstract_game import AbstractGame
from .poker_socket import PokerSocket
from .poker_engine_manager import PokerEngineManager


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
        
        # Enhanced action space with strategic raise sizing
        # 0=fold, 1=call, 2=check, 3-52=strategic raises, 53-102=linear raises
        self.action_space_size = 103
        self.min_raise = 2  # Big blind
        self.max_raise = 400  # Starting stack
        self.strategic_raises = [2, 3, 4, 6, 8, 12, 16, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 400]
        
        # Initialize random state if seed provided
        if seed is not None:
            np.random.seed(seed)
    
    def _encode_observation(self, message: dict) -> np.ndarray:
        """Convert poker socket message to MuZero observation vector with poker domain knowledge."""
        # Enhanced observation vector (250 dimensions)
        obs = np.zeros(250, dtype=np.float32)
        
        if not message:
            return obs
            
        # Game timing and meta-info (indices 0-9)
        if message.get('time_remaining'):
            obs[0] = min(message['time_remaining'] / 600.0, 1.0)
        if message.get('player_index') is not None:
            obs[1] = message['player_index']
        
        # Street encoding (0=preflop, 1=flop, 2=turn, 3=river)
        board_cards = message.get('board_cards', [])
        if len(board_cards) == 0:
            obs[2] = 1.0  # Preflop
        elif len(board_cards) == 3:
            obs[3] = 1.0  # Flop
        elif len(board_cards) == 4:
            obs[4] = 1.0  # Turn
        elif len(board_cards) >= 5:
            obs[5] = 1.0  # River
            
        # Hole cards (52 binary features) - indices 10-61
        hole_cards = message.get('hole_cards', [])
        for card in hole_cards[:2]:
            if card:
                card_idx = self._card_to_index(card)
                if card_idx >= 0:
                    obs[10 + card_idx] = 1.0
        
        # Board cards (52 binary features) - indices 62-113
        for card in board_cards[:5]:
            if card:
                card_idx = self._card_to_index(card)
                if card_idx >= 0:
                    obs[62 + card_idx] = 1.0
        
        # Hand strength features (indices 114-123)
        if hole_cards and board_cards:
            # Simplified hand strength calculation
            obs[114] = self._calculate_hand_strength(hole_cards, board_cards)
            obs[115] = len(set([c[0] for c in hole_cards]))  # Pair in hand
            obs[116] = len(set([c[1] for c in hole_cards]))  # Suited
            
        # Pot and betting info (indices 124-139)
        action_history = message.get('action_history', [])
        pot_size = 0
        raises_this_street = 0
        for action in action_history:
            if action.startswith('R'):
                pot_size += int(action[1:])
                raises_this_street += 1
            elif action in ['C', 'K']:
                pot_size += 2  # Assume big blind
                
        obs[124] = min(pot_size / 800.0, 1.0)  # Normalized pot size
        obs[125] = min(raises_this_street / 4.0, 1.0)  # Aggression level
        
        # Position and opponent modeling (indices 140-149)
        obs[140] = 1.0 if message.get('player_index') == 0 else 0.0  # Button position
        
        # Recent action history (last 8 actions) - indices 150-181
        for i, action in enumerate(action_history[-8:]):
            base_idx = 150 + i * 4
            if action == 'F':
                obs[base_idx] = 1.0
            elif action == 'C':
                obs[base_idx + 1] = 1.0
            elif action == 'K':
                obs[base_idx + 2] = 1.0
            elif action.startswith('R'):
                obs[base_idx + 3] = min(int(action[1:]) / 400.0, 1.0)
        
        # Bankroll and game state (indices 182-189)
        if message.get('bankroll_delta') is not None:
            obs[182] = message['bankroll_delta'] / 400.0
        
        # Bounty information (indices 190-199)
        bounty_hits = message.get('bounty_hits', '')
        if len(bounty_hits) >= 2:
            obs[190] = 1.0 if bounty_hits[0] == '1' else 0.0  # Our bounty hit
            obs[191] = 1.0 if bounty_hits[1] == '1' else 0.0  # Opponent bounty hit
            
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
        """Convert MuZero action index to poker protocol string with strategic sizing."""
        if action == 0:
            return 'F'  # Fold
        elif action == 1:
            return 'C'  # Call
        elif action == 2:
            return 'K'  # Check
        elif 3 <= action <= 20:  # Strategic raise sizes
            if action - 3 < len(self.strategic_raises):
                return f'R{self.strategic_raises[action - 3]}'
            else:
                return f'R{self.min_raise}'
        elif 21 <= action <= 102:  # Linear raise sizes for remaining actions
            raise_amount = self.min_raise + ((action - 21) * (self.max_raise - self.min_raise) // 81)
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
        """Return legal actions based on current game state."""
        if not hasattr(self, 'last_message') or not self.last_message:
            return list(range(self.action_space_size))
            
        # Parse last message to determine legal actions
        legal = []
        
        # Always can fold (except at end of hand)
        if not self.last_message.get('game_over', False):
            legal.append(0)  # Fold
        
        # Call/Check logic based on betting action
        action_history = self.last_message.get('action_history', [])
        last_action = action_history[-1] if action_history else None
        
        if last_action and last_action.startswith('R'):  # Facing a raise
            legal.append(1)  # Can call
            # Can re-raise if not all-in
            legal.extend(range(3, self.action_space_size))
        else:  # No raise to call
            legal.append(2)  # Can check
            # Can raise
            legal.extend(range(3, self.action_space_size))
            
        return legal
    
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