#!/usr/bin/env python3
"""
Direct test runner to avoid ROS/pytest conflicts.
Runs Phase 1 integration tests for poker socket and game.
"""

import sys
import os
import traceback

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def run_poker_socket_tests():
    """Run PokerSocket tests directly."""
    print("=== Testing PokerSocket Message Parsing ===")
    
    try:
        from games.poker_socket import PokerSocket
        
        # Test message parsing
        poker_socket = PokerSocket()
        
        # Mock socketfile for testing
        class MockSocketFile:
            def __init__(self, message):
                self.message = message
            def readline(self):
                return self.message
        
        # Test simple message
        poker_socket.socketfile = MockSocketFile("T600.000 P0 H7s,8s")
        message = poker_socket.receive_message()
        
        assert message['time_remaining'] == 600.0
        assert message['player_index'] == 0
        assert message['hole_cards'] == ['7s', '8s']
        print("✓ Simple message parsing works")
        
        # Test full game message
        poker_socket.socketfile = MockSocketFile("T599.200 P0 H7s,8s B9h,Td,Jc O2c,2d D-50 Q")
        message = poker_socket.receive_message()
        
        assert message['hole_cards'] == ['7s', '8s']
        assert message['board_cards'] == ['9h', 'Td', 'Jc']
        assert message['opponent_hand'] == ['2c', '2d']
        assert message['bankroll_delta'] == -50
        assert message['game_over'] is True
        print("✓ Full game message parsing works")
        
        return True
        
    except Exception as e:
        print(f"✗ PokerSocket tests failed: {e}")
        traceback.print_exc()
        return False

def run_poker_game_tests():
    """Run PokerGame tests directly."""
    print("\n=== Testing PokerGame Interface ===")
    
    try:
        from games.poker_game import PokerGame
        import numpy as np
        
        # Test initialization
        game = PokerGame(seed=42, training_mode=True)
        assert game.action_space_size == 103
        assert game.training_mode is True
        print("✓ Game initialization works")
        
        # Test observation encoding
        message = {
            'time_remaining': 300.0,
            'player_index': 0,
            'hole_cards': ['As', 'Kh'],
            'bankroll_delta': 50
        }
        
        obs = game._encode_observation(message)
        assert obs.shape == (200,)
        assert obs[0] == 0.5  # 300/600 normalized
        assert obs[1] == 0    # player index
        print("✓ Observation encoding works")
        
        # Test card to index conversion
        assert game._card_to_index('As') == 48  # Ace of spades
        assert game._card_to_index('2s') == 0   # 2 of spades
        assert game._card_to_index('Xs') == -1  # Invalid
        print("✓ Card indexing works")
        
        # Test action to poker code conversion
        assert game._action_to_poker_code(0) == 'F'
        assert game._action_to_poker_code(1) == 'C'
        assert game._action_to_poker_code(2) == 'K'
        assert game._action_to_poker_code(3) == 'R2'
        print("✓ Action encoding works")
        
        # Test action string conversion
        assert game.action_to_string(0) == "Fold"
        assert game.action_to_string(1) == "Call"
        assert "Raise" in game.action_to_string(50)
        print("✓ Action string conversion works")
        
        # Test legal actions
        actions = game.legal_actions()
        assert len(actions) == 103
        assert actions == list(range(103))
        print("✓ Legal actions works")
        
        game.close()
        return True
        
    except Exception as e:
        print(f"✗ PokerGame tests failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all Phase 1 tests."""
    print("Running Phase 1 Integration Tests")
    print("=" * 40)
    
    socket_tests_pass = run_poker_socket_tests()
    game_tests_pass = run_poker_game_tests()
    
    print("\n" + "=" * 40)
    if socket_tests_pass and game_tests_pass:
        print("✓ All Phase 1 tests PASSED")
        return 0
    else:
        print("✗ Some Phase 1 tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())