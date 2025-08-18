"""
Phase 2 tests for enhanced poker integration.
Tests state representation, action space improvements, and engine management.
"""

import sys
import os
import tempfile
import shutil
import numpy as np

# Add games directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../games'))

from poker_game import PokerGame
from poker_engine_manager import PokerEngineManager


class TestEnhancedStateRepresentation:
    """Test enhanced observation encoding with poker domain knowledge."""
    
    def setup_method(self):
        self.game = PokerGame(training_mode=True)
    
    def test_enhanced_observation_dimensions(self):
        """Test that enhanced observation has correct dimensions."""
        message = {'time_remaining': 300.0, 'hole_cards': ['As', 'Kh']}
        obs = self.game._encode_observation(message)
        assert obs.shape == (250,), f"Expected (250,) but got {obs.shape}"
        print("✓ Enhanced observation dimensions correct")
    
    def test_street_encoding(self):
        """Test street (betting round) encoding in observation."""
        # Preflop
        message = {'board_cards': []}
        obs = self.game._encode_observation(message)
        assert obs[2] == 1.0  # Preflop indicator
        
        # Flop
        message = {'board_cards': ['9h', 'Td', 'Jc']}
        obs = self.game._encode_observation(message)
        assert obs[3] == 1.0  # Flop indicator
        
        # Turn
        message = {'board_cards': ['9h', 'Td', 'Jc', 'Qs']}
        obs = self.game._encode_observation(message)
        assert obs[4] == 1.0  # Turn indicator
        
        # River
        message = {'board_cards': ['9h', 'Td', 'Jc', 'Qs', 'Ah']}
        obs = self.game._encode_observation(message)
        assert obs[5] == 1.0  # River indicator
        
        print("✓ Street encoding works correctly")
    
    def test_hand_strength_calculation(self):
        """Test simplified hand strength calculation."""
        # Test pocket aces (should be high strength)
        strength = self.game._calculate_hand_strength(['As', 'Ah'], [])\n        assert strength > 0.6, f\"Pocket aces should have high strength, got {strength}\"\n        \n        # Test low cards (should be low strength)\n        strength = self.game._calculate_hand_strength(['2s', '3h'], [])\n        assert strength < 0.3, f\"Low cards should have low strength, got {strength}\"\n        \n        # Test suited cards (should get bonus)\n        suited_strength = self.game._calculate_hand_strength(['7s', '8s'], [])\n        offsuit_strength = self.game._calculate_hand_strength(['7s', '8h'], [])\n        assert suited_strength > offsuit_strength, \"Suited cards should be stronger\"\n        \n        print(\"✓ Hand strength calculation works\")\n    \n    def test_strategic_action_space(self):
        \"\"\"Test strategic raise sizing in action space.\"\"\"\n        # Test strategic raises (actions 3-20)\n        assert self.game._action_to_poker_code(3) == 'R2'  # Min raise\n        assert self.game._action_to_poker_code(4) == 'R3'  # Small raise\n        assert self.game._action_to_poker_code(10) == 'R12'  # Medium raise\n        \n        # Test linear raises (actions 21-102)\n        linear_action = self.game._action_to_poker_code(50)\n        assert linear_action.startswith('R')\n        \n        print(\"✓ Strategic action space works\")\n\n\nclass TestEngineManager:\n    \"\"\"Test engine process lifecycle management.\"\"\"\n    \n    def setup_method(self):\n        self.manager = PokerEngineManager()\n    \n    def teardown_method(self):\n        if self.manager:\n            self.manager.stop_engine()\n            self.manager.cleanup_training_dir()\n    \n    def test_training_environment_creation(self):\n        \"\"\"Test creation of isolated training environment.\"\"\"\n        config_overrides = {\n            'STARTING_GAME_CLOCK': 1200.0,\n            'NUM_ROUNDS': 50\n        }\n        \n        training_dir = self.manager.create_training_environment(config_overrides)\n        \n        # Check directory was created\n        assert os.path.exists(training_dir)\n        \n        # Check config file was created\n        config_path = os.path.join(training_dir, \"config.py\")\n        assert os.path.exists(config_path)\n        \n        # Verify config content\n        with open(config_path, 'r') as f:\n            content = f.read()\n            assert 'STARTING_GAME_CLOCK = 1200.0' in content\n            assert 'NUM_ROUNDS = 50' in content\n            \n        print(\"✓ Training environment creation works\")\n    \n    def test_muzero_bot_stub_creation(self):\n        \"\"\"Test creation of MuZero bot stub.\"\"\"\n        self.manager.create_training_environment()\n        bot_dir = self.manager.create_muzero_bot_stub()\n        \n        # Check bot directory and files\n        assert os.path.exists(bot_dir)\n        assert os.path.exists(os.path.join(bot_dir, \"commands.json\"))\n        assert os.path.exists(os.path.join(bot_dir, \"player.py\"))\n        \n        # Check commands.json format\n        with open(os.path.join(bot_dir, \"commands.json\"), 'r') as f:\n            import json\n            commands = json.load(f)\n            assert 'build' in commands\n            assert 'run' in commands\n            \n        print(\"✓ MuZero bot stub creation works\")\n    \n    def test_config_generation_with_overrides(self):\n        \"\"\"Test config generation with various override scenarios.\"\"\"\n        # Test minimal overrides\n        overrides = {'NUM_ROUNDS': 10}\n        self.manager.create_training_environment(overrides)\n        \n        with open(self.manager.config_file, 'r') as f:\n            content = f.read()\n            assert 'NUM_ROUNDS = 10' in content\n            assert 'STARTING_GAME_CLOCK = 3600.0' in content  # Default\n            \n        print(\"✓ Config generation with overrides works\")\n\n\nclass TestLegalActionFiltering:\n    \"\"\"Test improved legal action filtering.\"\"\"\n    \n    def setup_method(self):\n        self.game = PokerGame(training_mode=True)\n    \n    def test_preflop_legal_actions(self):\n        \"\"\"Test legal actions on preflop.\"\"\"\n        message = {\n            'board_cards': [],\n            'action_history': [],\n            'game_over': False\n        }\n        \n        self.game.last_message = message\n        legal = self.game.legal_actions()\n        \n        # Should include fold, check, and raises\n        assert 0 in legal  # Fold\n        assert 2 in legal  # Check (no bet to call)\n        assert len(legal) > 50  # Many raise options\n        \n        print(\"✓ Preflop legal actions correct\")\n    \n    def test_facing_bet_legal_actions(self):\n        \"\"\"Test legal actions when facing a bet.\"\"\"\n        message = {\n            'board_cards': ['9h', 'Td', 'Jc'],\n            'action_history': ['R20'],  # Opponent raised 20\n            'game_over': False\n        }\n        \n        self.game.last_message = message\n        legal = self.game.legal_actions()\n        \n        # Should include fold, call, and re-raises\n        assert 0 in legal  # Fold\n        assert 1 in legal  # Call\n        assert 2 not in legal  # Cannot check when facing bet\n        assert len([a for a in legal if a >= 3]) > 0  # Re-raise options\n        \n        print(\"✓ Facing bet legal actions correct\")\n\n\ndef run_phase2_tests():\n    \"\"\"Run all Phase 2 tests.\"\"\"\n    print(\"Running Phase 2 Integration Tests\")\n    print(\"=\" * 40)\n    \n    try:\n        # Test enhanced state representation\n        print(\"\\n=== Enhanced State Representation ===\")\n        test_state = TestEnhancedStateRepresentation()\n        test_state.setup_method()\n        test_state.test_enhanced_observation_dimensions()\n        test_state.test_street_encoding()\n        test_state.test_hand_strength_calculation()\n        test_state.test_strategic_action_space()\n        \n        # Test engine manager\n        print(\"\\n=== Engine Process Management ===\")\n        test_engine = TestEngineManager()\n        test_engine.setup_method()\n        test_engine.test_training_environment_creation()\n        test_engine.test_muzero_bot_stub_creation()\n        test_engine.test_config_generation_with_overrides()\n        test_engine.teardown_method()\n        \n        # Test legal action filtering\n        print(\"\\n=== Legal Action Filtering ===\")\n        test_legal = TestLegalActionFiltering()\n        test_legal.setup_method()\n        test_legal.test_preflop_legal_actions()\n        test_legal.test_facing_bet_legal_actions()\n        \n        print(\"\\n\" + \"=\" * 40)\n        print(\"✓ All Phase 2 tests PASSED\")\n        return True\n        \n    except Exception as e:\n        print(f\"\\n✗ Phase 2 tests FAILED: {e}\")\n        import traceback\n        traceback.print_exc()\n        return False\n\n\nif __name__ == \"__main__\":\n    success = run_phase2_tests()\n    sys.exit(0 if success else 1)