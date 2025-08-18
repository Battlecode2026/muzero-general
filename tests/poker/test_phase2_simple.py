"""
Simplified Phase 2 tests for enhanced poker integration.
"""

import sys
import os
import numpy as np

# Add games directory to path
games_dir = os.path.join(os.path.dirname(__file__), '../../games')
sys.path.append(games_dir)
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))


def test_enhanced_observations():
    """Test enhanced observation encoding."""
    print("=== Testing Enhanced Observations ===")
    
    game = PokerGame(training_mode=True)
    
    # Test dimensions
    message = {'time_remaining': 300.0, 'hole_cards': ['As', 'Kh']}
    obs = game._encode_observation(message)
    assert obs.shape == (250,), f"Expected (250,) but got {obs.shape}"
    print("✓ Enhanced observation dimensions correct")
    
    # Test street encoding
    message = {'board_cards': ['9h', 'Td', 'Jc']}
    obs = game._encode_observation(message)
    assert obs[3] == 1.0, "Flop indicator should be set"
    print("✓ Street encoding works")
    
    return True


def test_strategic_action_space():
    """Test strategic raise sizing."""
    print("\\n=== Testing Strategic Action Space ===")
    
    game = PokerGame(training_mode=True)
    
    # Test basic actions
    assert game._action_to_poker_code(0) == 'F'
    assert game._action_to_poker_code(1) == 'C'
    assert game._action_to_poker_code(2) == 'K'
    print("✓ Basic actions work")
    
    # Test strategic raises
    assert game._action_to_poker_code(3) == 'R2'
    assert game._action_to_poker_code(4) == 'R3'
    print("✓ Strategic raises work")
    
    return True


def test_engine_manager():
    """Test engine process management."""
    print("\\n=== Testing Engine Manager ===")
    
    manager = PokerEngineManager()
    
    try:
        # Test config creation
        training_dir = manager.create_training_environment({'NUM_ROUNDS': 50})
        assert os.path.exists(training_dir)
        print("✓ Training environment creation works")
        
        # Test bot stub creation
        bot_dir = manager.create_muzero_bot_stub()
        assert os.path.exists(bot_dir)
        assert os.path.exists(os.path.join(bot_dir, "commands.json"))
        print("✓ Bot stub creation works")
        
        return True
        
    finally:
        manager.cleanup_training_dir()


def test_legal_actions():
    """Test legal action filtering."""
    print("\\n=== Testing Legal Actions ===")
    
    game = PokerGame(training_mode=True)
    
    # Test default legal actions
    legal = game.legal_actions()
    assert len(legal) == 103
    print("✓ Default legal actions work")
    
    # Test with message
    game.last_message = {
        'board_cards': [],
        'action_history': [],
        'game_over': False
    }
    legal = game.legal_actions()
    assert 0 in legal  # Fold
    assert 2 in legal  # Check
    print("✓ Message-based legal actions work")
    
    return True


def main():
    """Run all Phase 2 tests."""
    print("Running Phase 2 Integration Tests")
    print("=" * 40)
    
    try:
        success = True
        success &= test_enhanced_observations()
        success &= test_strategic_action_space()
        success &= test_engine_manager()
        success &= test_legal_actions()
        
        print("\\n" + "=" * 40)
        if success:
            print("✓ All Phase 2 tests PASSED")
            return 0
        else:
            print("✗ Some Phase 2 tests FAILED")
            return 1
            
    except Exception as e:
        print(f"\\n✗ Phase 2 tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())