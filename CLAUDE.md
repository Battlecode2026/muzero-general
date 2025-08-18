# CLAUDE.md - MuZero General

This file provides guidance to Claude Code when working with the MuZero reinforcement learning component.

## Memory Management
**IMPORTANT**: Update this file with new insights about:
- Training performance and convergence patterns for poker
- Network architecture adjustments and their results
- Hyperparameter tuning outcomes and optimal settings
- Ray framework integration issues and solutions
- MCTS optimization techniques for time-constrained environments

## Component Overview

MuZero General is a reinforcement learning implementation of the MuZero algorithm designed for various games and environments. It learns a model of the environment and uses internal representations for predicting rewards, values, policies, and transitions.

## Key Files and Structure

### Core Implementation
- `muzero.py` - Main training entry point
- `models.py` - Neural network architectures (residual and fully connected)
- `trainer.py` - Training loop implementation
- `self_play.py` - Self-play data generation
- `replay_buffer.py` - Experience replay management
- `shared_storage.py` - Shared model storage for distributed training

### Game Interface
- `games/abstract_game.py` - Abstract base class that all games must inherit
- `games/` - Game implementations (cartpole, lunarlander, connect4, tictactoe, etc.)

### Key Abstract Methods to Implement
From `abstract_game.py`:
- `__init__(self, seed=None)` - Initialize game
- `step(action)` - Apply action, return observation/reward/done
- `legal_actions()` - Return valid actions for current state
- `reset()` - Reset game to initial state
- `render()` - Display current game state

### Optional Methods
- `to_play()` - Return current player (defaults to 0)
- `expert_agent()` - Hard-coded opponent for assessment
- `action_to_string(action)` - Convert action number to string

## Development Commands

### Installation
```bash
cd lib/muzero-general
pip install -r requirements.lock
```

### Training
```bash
python muzero.py
```

### Monitoring
```bash
tensorboard --logdir ./results
```

### Model Diagnosis
```bash
python diagnose_model.py
```

## Dependencies
- Python >= 3.6
- PyTorch (neural networks)
- Ray (distributed training)
- TensorBoard (monitoring)
- Gym environments (optional)

## Configuration

Each game has a `MuZeroConfig` class containing:
- Network architecture settings
- Training hyperparameters
- MCTS parameters
- Environment-specific settings

## Training Architecture

### Multi-threaded Design
- Self-play workers generate training data
- Training worker updates neural networks
- Shared storage coordinates model weights
- Ray framework manages distributed execution

### Neural Networks
- **Representation network**: Encodes observations to hidden state
- **Dynamics network**: Predicts next hidden state and reward
- **Prediction network**: Outputs value and policy from hidden state

## Poker Bot Integration Implementation

### Integration Architecture
Create `games/poker.py` that bridges MuZero with the MIT Pokerbots Engine via socket communication.

### Implementation Phases

#### Phase 1: Foundation (Days 1-2) ✓ COMPLETED
- **PokerSocket Class**: Handle engine subprocess and socket I/O ✓
- **PokerGame Skeleton**: Basic `AbstractGame` implementation ✓
- **Unit Tests**: Mock socket communication, interface compliance ✓

#### Phase 2: Core Integration (Days 3-5) ✓ COMPLETED
- **State Representation**: Parse poker socket messages (`T#.###`, `H**,**`, `B**,**`, etc.) into 250-dim observation tensors ✓
- **Action Space**: Strategic raise sizing with 18 common bet sizes + 82 linear raises ✓
- **Process Management**: Engine lifecycle with isolated training environments and config generation ✓

#### Phase 3: Timeout Handling (Days 6-7) - CRITICAL
- **Adaptive Time Allocation**: Limit MCTS search based on remaining game clock
- **Training Extensions**: Increase `STARTING_GAME_CLOCK` from 60s to 600s+ for training
- **Timeout Recovery**: Graceful degradation when approaching time limits

#### Phase 4: Training Integration (Days 8-10)
- **Poker Config**: Network architecture for poker observations (~100-200 dim)
- **Hyperparameters**: MCTS simulations, learning rates, replay buffer size
- **Multi-Game Loop**: Batch training with engine restarts between games

#### Phase 5: Validation (Days 11-12)
- **End-to-End Tests**: Full training pipeline validation
- **Performance Benchmarks**: Against random/rule-based opponents

### Key Challenges
1. **Game Clock Management**: 60s total clock vs MCTS computational needs
2. **Socket Protocol**: Parse engine messages into structured observations
3. **Action Discretization**: Map continuous raise amounts to learnable actions
4. **Hidden Information**: Handle opponent cards and stochastic board reveals
5. **Reward Engineering**: Balance immediate pot wins vs long-term strategy

### Implementation Status Update

#### Completed Components (Phases 1-2)
- **`poker_socket.py`**: Socket communication with message parsing and action encoding
- **`poker_game.py`**: AbstractGame implementation with 250-dim observations and 103-action space
- **`poker_engine_manager.py`**: Process management with isolated training environments
- **Test Suite**: Direct Python testing (bypassed ROS/pytest conflicts)
- **Config Generation**: Extended timeouts (3600s) and custom training parameters

#### Key Enhancements Made
- **Strategic Action Space**: 18 strategic raises (2BB, 3BB, pot-sized) + linear sizing
- **Enhanced Observations**: Street encoding, hand strength, pot info, betting history
- **Robust Error Handling**: Connection failures, malformed messages, timeout detection
- **Training Isolation**: Temporary directories with custom configs and bot stubs

### Testing Requirements ✓ IMPLEMENTED
- Mock engine responses for unit testing ✓
- Integration tests with config generation and bot stub creation ✓
- Direct Python test execution (avoiding external dependencies) ✓
- Core functionality validation complete ✓

### Next Priority: Phase 3 Timeout Handling
Critical path implementation needed for MCTS time management and game clock integration.