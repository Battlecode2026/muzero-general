"""
Unit tests for PokerSocket class.
Tests socket communication, message parsing, and engine process management.
"""

import pytest
import time
import os
from unittest.mock import patch, MagicMock
import sys

# Add games directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../games'))

from poker_socket import PokerSocket
from mocks.mock_engine import MockPokerEngine, MockPokerScenarios


class TestPokerSocket:
    """Test suite for PokerSocket functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_engine = MockPokerEngine(port=12346)
        self.poker_socket = PokerSocket()
    
    def teardown_method(self):
        """Clean up after tests."""
        if self.mock_engine:
            self.mock_engine.stop()
        if self.poker_socket:
            self.poker_socket.close()
    
    def test_message_parsing_simple(self):
        """Test parsing of basic poker socket messages."""
        # Test simple message parsing without socket connection
        test_message = "T600.000 P0 H7s,8s"
        
        # Mock socketfile for testing
        mock_socketfile = MagicMock()
        mock_socketfile.readline.return_value = test_message
        
        self.poker_socket.socketfile = mock_socketfile
        message = self.poker_socket.receive_message()
        
        assert message is not None
        assert message['time_remaining'] == 600.0
        assert message['player_index'] == 0
        assert message['hole_cards'] == ['7s', '8s']
        assert message['game_over'] is False
    
    def test_message_parsing_full_game(self):
        """Test parsing of complete game message."""
        test_message = "T599.200 P0 H7s,8s B9h,Td,Jc,Qs,Ah BActs C O2c,2d D-50 Q"
        
        mock_socketfile = MagicMock()
        mock_socketfile.readline.return_value = test_message
        
        self.poker_socket.socketfile = mock_socketfile
        message = self.poker_socket.receive_message()
        
        assert message['time_remaining'] == 599.2
        assert message['hole_cards'] == ['7s', '8s']
        assert message['board_cards'] == ['9h', 'Td', 'Jc', 'Qs', 'Ah']
        assert message['opponent_hand'] == ['2c', '2d']
        assert message['bankroll_delta'] == -50
        assert message['game_over'] is True
    
    def test_action_encoding(self):
        """Test action encoding to poker protocol format."""
        mock_socketfile = MagicMock()
        self.poker_socket.socketfile = mock_socketfile
        
        # Test fold
        self.poker_socket.send_action('F')
        mock_socketfile.write.assert_called_with('F\n')
        
        # Test call
        self.poker_socket.send_action('C')
        mock_socketfile.write.assert_called_with('C\n')
        
        # Test raise
        self.poker_socket.send_action('R50')
        mock_socketfile.write.assert_called_with('R50\n')
    
    def test_connection_failure_handling(self):
        """Test handling of connection failures."""
        # Test with non-existent port
        result = self.poker_socket.connect(port=99999)
        assert result is False
        assert not self.poker_socket.is_connected()
    
    def test_config_file_creation(self):
        """Test training config file generation."""
        config_overrides = {
            'STARTING_GAME_CLOCK': 900.0,
            'NUM_ROUNDS': 100
        }
        
        poker_socket = PokerSocket(config_overrides=config_overrides)
        config_path = poker_socket._create_training_config()
        
        assert os.path.exists(config_path)
        
        # Read and verify config content
        with open(config_path, 'r') as f:
            content = f.read()
            assert 'STARTING_GAME_CLOCK = 900.0' in content
            assert 'NUM_ROUNDS = 100' in content
        
        # Clean up
        os.remove(config_path)
    
    @pytest.mark.integration
    def test_mock_engine_communication(self):
        """Test communication with mock engine."""
        # Set up mock engine with responses
        self.mock_engine.add_response("T600.000 P0 H2s,3h")
        self.mock_engine.add_response("T599.500 P0 H2s,3h BActs F D2 Q")
        
        assert self.mock_engine.start()
        time.sleep(0.5)  # Give mock engine time to start
        
        # Test connection
        assert self.poker_socket.connect(port=12346)
        assert self.poker_socket.is_connected()
        
        # Test message reception
        message1 = self.poker_socket.receive_message()
        assert message1['time_remaining'] == 600.0
        assert message1['hole_cards'] == ['2s', '3h']
        
        # Test action sending
        assert self.poker_socket.send_action('F')
        
        # Test final message
        message2 = self.poker_socket.receive_message()
        assert message2['game_over'] is True
        assert message2['bankroll_delta'] == 2
        
        # Verify mock engine received our action
        received_actions = self.mock_engine.get_received_actions()
        assert 'F' in received_actions


class TestPokerSocketEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_malformed_messages(self):
        """Test handling of malformed socket messages."""
        poker_socket = PokerSocket()
        
        mock_socketfile = MagicMock()
        mock_socketfile.readline.return_value = "INVALID MESSAGE FORMAT"
        poker_socket.socketfile = mock_socketfile
        
        message = poker_socket.receive_message()
        # Should not crash, may return empty/default message
        assert message is not None
    
    def test_empty_messages(self):
        """Test handling of empty socket messages."""
        poker_socket = PokerSocket()
        
        mock_socketfile = MagicMock()
        mock_socketfile.readline.return_value = ""
        poker_socket.socketfile = mock_socketfile
        
        message = poker_socket.receive_message()
        assert message is None
    
    def test_partial_card_data(self):
        """Test handling of incomplete card information."""
        poker_socket = PokerSocket()
        
        mock_socketfile = MagicMock()
        mock_socketfile.readline.return_value = "T600.000 P0 H2s B9h,Td"
        poker_socket.socketfile = mock_socketfile
        
        message = poker_socket.receive_message()
        assert len(message['hole_cards']) == 1
        assert len(message['board_cards']) == 2