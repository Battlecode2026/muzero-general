"""
Unit tests for PokerGame class.
Tests AbstractGame interface compliance and poker-specific functionality.
"""

import pytest
import numpy as np
import sys
import os
from unittest.mock import patch, MagicMock

# Add games directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../games'))

from poker_game import PokerGame
from mocks.mock_engine import MockPokerEngine, MockPokerScenarios


class TestPokerGame:
    """Test suite for PokerGame AbstractGame implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game = PokerGame(seed=42, training_mode=True)
    
    def teardown_method(self):
        """Clean up after tests."""
        if self.game:
            self.game.close()
    
    def test_initialization(self):
        """Test game initialization."""
        assert self.game.training_mode is True
        assert self.game.seed == 42
        assert self.game.action_space_size == 103
        assert self.game.game_over is False
    
    def test_observation_encoding_empty(self):
        """Test observation encoding with empty message."""
        obs = self.game._encode_observation({})
        assert obs.shape == (200,)
        assert obs.dtype == np.float32
        assert np.all(obs == 0)
    
    def test_observation_encoding_full(self):
        """Test observation encoding with complete message."""
        message = {
            'time_remaining': 300.0,
            'player_index': 0,
            'hole_cards': ['As', 'Kh'],
            'board_cards': ['9h', 'Td', 'Jc'],
            'action_history': ['C', 'R10', 'F'],
            'bankroll_delta': 50
        }
        
        obs = self.game._encode_observation(message)
        
        # Check time encoding
        assert obs[0] == 0.5  # 300/600
        
        # Check player index
        assert obs[1] == 0
        
        # Check hole cards are encoded (As should be index 48, Kh should be index 49)
        assert obs[2 + 48] == 1.0  # As
        assert obs[2 + 49] == 1.0  # Kh
        
        # Check bankroll delta
        assert obs[146] == 50/400.0  # Normalized by starting stack
    
    def test_card_to_index_conversion(self):
        """Test card string to index conversion."""
        # Test valid cards
        assert self.game._card_to_index('2s') == 0   # 2 of spades
        assert self.game._card_to_index('As') == 48  # Ace of spades  
        assert self.game._card_to_index('Ah') == 49  # Ace of hearts
        assert self.game._card_to_index('Kd') == 46  # King of diamonds
        
        # Test invalid cards
        assert self.game._card_to_index('Xs') == -1  # Invalid rank
        assert self.game._card_to_index('2x') == -1  # Invalid suit
        assert self.game._card_to_index('A') == -1   # Too short
        assert self.game._card_to_index('') == -1    # Empty
    
    def test_action_to_poker_code(self):
        """Test MuZero action to poker protocol conversion."""
        # Test basic actions
        assert self.game._action_to_poker_code(0) == 'F'  # Fold
        assert self.game._action_to_poker_code(1) == 'C'  # Call
        assert self.game._action_to_poker_code(2) == 'K'  # Check
        
        # Test raise actions
        assert self.game._action_to_poker_code(3) == 'R2'   # Min raise
        assert self.game._action_to_poker_code(102) == 'R400'  # Max raise
        
        # Test invalid action (should default to check)
        assert self.game._action_to_poker_code(999) == 'K'
    
    def test_legal_actions(self):
        """Test legal actions method."""
        actions = self.game.legal_actions()
        assert len(actions) == 103
        assert actions == list(range(103))
    
    def test_action_to_string(self):
        """Test action number to string conversion."""
        assert self.game.action_to_string(0) == "Fold"
        assert self.game.action_to_string(1) == "Call"
        assert self.game.action_to_string(2) == "Check"
        assert "Raise" in self.game.action_to_string(50)
        assert "Unknown" in self.game.action_to_string(999)
    
    @patch('games.poker_socket.PokerSocket')
    def test_step_with_mocked_socket(self, mock_socket_class):
        """Test step method with mocked socket communication."""
        # Set up mock
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.send_action.return_value = True
        mock_socket.receive_message.return_value = {
            'time_remaining': 590.0,
            'bankroll_delta': 10,
            'game_over': False
        }
        
        # Initialize game with mock
        game = PokerGame(training_mode=True)
        game.poker_socket = mock_socket
        game.current_observation = np.zeros(200)
        
        # Test step
        obs, reward, done = game.step(1)  # Call action
        
        assert obs.shape == (200,)
        assert reward == 10/400.0  # Normalized reward
        assert done is False
        mock_socket.send_action.assert_called_with('C')
    
    def test_step_connection_failure(self):
        """Test step method when socket connection fails."""
        # Mock failed socket
        mock_socket = MagicMock()
        mock_socket.send_action.return_value = False
        
        self.game.poker_socket = mock_socket
        self.game.current_observation = np.zeros(200)
        
        obs, reward, done = self.game.step(1)
        
        assert reward == -1.0  # Penalty for connection failure
        assert done is True
        assert self.game.game_over is True


class TestPokerGameIntegration:
    """Integration tests with mock engine."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.mock_engine = MockPokerEngine(port=12347)
        
    def teardown_method(self):
        """Clean up integration tests."""
        if self.mock_engine:
            self.mock_engine.stop()
    
    @pytest.mark.integration  
    @patch.object(PokerSocket, 'start_engine')
    @patch.object(PokerSocket, 'connect')
    def test_full_game_cycle(self, mock_connect, mock_start_engine):
        """Test complete game cycle with mock responses."""
        # Set up mocks
        mock_start_engine.return_value = True
        mock_connect.return_value = True
        
        # Set up mock engine responses
        responses = MockPokerScenarios.simple_hand()
        
        game = PokerGame(training_mode=True)
        
        # Mock the socket communication
        mock_messages = [
            {'time_remaining': 600.0, 'hole_cards': ['2s', '3h'], 'game_over': False},
            {'time_remaining': 599.5, 'bankroll_delta': 2, 'game_over': True}
        ]
        
        with patch.object(game.poker_socket, 'receive_message', side_effect=mock_messages):
            with patch.object(game.poker_socket, 'send_action', return_value=True):
                # Test reset
                obs = game.reset()
                assert obs.shape == (200,)
                
                # Test step
                obs, reward, done = game.step(0)  # Fold
                assert reward == 2/400.0
                assert done is True