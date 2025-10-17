# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an implementation scaffold for reproducing the Agentic Context Engineering (ACE) method from the paper "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models" (arXiv:2510.04618).

## Development Commands

### Dependency Management (pip-tools)
This project uses pip-tools for automatic dependency locking to prevent version mismatch bugs.

```bash
# Install dependencies (for users)
pip install -r requirements.txt

# Development workflow (for contributors)
pip install pip-tools

# Update dependencies: edit requirements.in, then run:
pip-compile requirements.in

# Sync your environment to match requirements.txt exactly
pip-sync requirements.txt

# Add new dependency: add to requirements.in, then compile
echo "new-package>=1.0.0" >> requirements.in
pip-compile requirements.in
```

**Files:**
- `requirements.in` - High-level dependencies (edit this)
- `requirements.txt` - Locked dependencies with exact versions (auto-generated)

### Running Tests
```bash
# Run all tests
python -m unittest discover -s tests

# Run specific test file
python -m unittest tests.test_adaptation

# Run with verbose output
python -m unittest discover -s tests -v
```

### Running Example Scripts
```bash
# Run the Kayba Test demo (seahorse emoji challenge)
python examples/kayba_ace_test.py

# Run questions with ACE adaptation (requires model weights)
CUDA_VISIBLE_DEVICES=2,3 python scripts/run_questions.py

# Run local adapter with Transformers model
CUDA_VISIBLE_DEVICES=2,3 python scripts/run_local_adapter.py

# Run direct questions without adaptation
python scripts/run_questions_direct.py
```

## Architecture

### Core Concepts
- **Playbook**: Structured context store containing bullets (strategy entries) with helpful/harmful counters
- **Delta Operations**: Incremental updates to the playbook (ADD, UPDATE, TAG, REMOVE)
- **Three Agentic Roles** sharing the same base LLM:
  - **Generator**: Produces answers using the current playbook
  - **Reflector**: Analyzes errors and classifies bullet contributions
  - **Curator**: Emits delta operations to update the playbook

### Module Structure

**ace/** - Core library modules:
- `playbook.py`: Bullet and Playbook classes for context storage
- `delta.py`: DeltaOperation and DeltaBatch for incremental updates
- `roles.py`: Generator, Reflector, Curator implementations
- `adaptation.py`: OfflineAdapter and OnlineAdapter orchestration loops
- `llm.py`: LLMClient interface with DummyLLMClient and TransformersLLMClient
- `prompts.py`: Default prompt templates for each role

**tests/** - Test suite using unittest framework

**scripts/** - Example usage and evaluation scripts

### Key Implementation Patterns

1. **Adaptation Flow**:
   - Sample → Generator (produces answer) → Environment (evaluates) → Reflector (analyzes) → Curator (updates playbook)
   - Offline: Multiple epochs over training samples
   - Online: Sequential processing of test samples

2. **LLM Integration**:
   - Implement `LLMClient` subclass for your model API
   - TransformersLLMClient provided for local model deployment
   - All roles share the same LLM instance

3. **Task Environment**:
   - Extend `TaskEnvironment` abstract class
   - Implement `evaluate()` to provide execution feedback
   - Return `EnvironmentResult` with feedback and optional ground truth

## Python Requirements
- Python 3.9+ (developed with 3.12)
- Dependencies managed via pip-tools (see requirements.in/requirements.txt)
- Core: LiteLLM, Pydantic, Python-dotenv, Rich
- Optional: transformers library for TransformersLLMClient