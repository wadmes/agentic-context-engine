#!/usr/bin/env python3
"""Syntax check for the README starter example."""

import sys

def test_imports():
    """Test that all imports work."""
    try:
        from ace import (
            OfflineAdapter, Generator, Reflector, Curator,
            LiteLLMClient, Sample, TaskEnvironment, EnvironmentResult, Playbook
        )
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_class_creation():
    """Test that we can create the environment class."""
    from ace import TaskEnvironment, EnvironmentResult, Sample
    from ace.roles import GeneratorOutput

    # Define a simple environment for math problems
    class MathEnvironment(TaskEnvironment):
        def evaluate(self, sample, generator_output):
            question = sample.question
            final_answer = generator_output.final_answer

            # Check if the answer is correct
            if "2+2" in question and final_answer.strip() == "4":
                return EnvironmentResult(feedback="Correct!", ground_truth="4")
            elif "5*3" in question and final_answer.strip() == "15":
                return EnvironmentResult(feedback="Correct!", ground_truth="15")
            else:
                return EnvironmentResult(feedback="Let me check that calculation.")

    # Test instantiation
    env = MathEnvironment()
    print("✓ MathEnvironment class created successfully")

    # Test with mock data
    sample = Sample(question="What is 2+2?", ground_truth="4")

    # Create a mock generator output
    from dataclasses import dataclass
    from typing import List, Dict, Any

    @dataclass
    class MockGeneratorOutput:
        reasoning: str = "Calculating..."
        final_answer: str = "4"
        bullet_ids: List[str] = None
        raw: Dict[str, Any] = None

        def __post_init__(self):
            if self.bullet_ids is None:
                self.bullet_ids = []
            if self.raw is None:
                self.raw = {}

    mock_output = MockGeneratorOutput(final_answer="4")
    result = env.evaluate(sample, mock_output)

    assert result.feedback == "Correct!"
    assert result.ground_truth == "4"
    print("✓ MathEnvironment.evaluate() works correctly")

    return True

def test_sample_creation():
    """Test that samples can be created."""
    from ace import Sample

    samples = [
        Sample(question="What is 2+2?", ground_truth="4"),
        Sample(question="What is 5*3?", ground_truth="15")
    ]

    assert len(samples) == 2
    assert samples[0].question == "What is 2+2?"
    assert samples[0].ground_truth == "4"
    print("✓ Sample creation successful")
    return True

def test_component_creation():
    """Test that all components can be created."""
    from ace import Generator, Reflector, Curator, Playbook, OfflineAdapter, DummyLLMClient

    # Create a dummy client
    client = DummyLLMClient()

    # Create the three ACE roles
    generator = Generator(client)
    reflector = Reflector(client)
    curator = Curator(client)

    # Create an adapter with an empty playbook
    adapter = OfflineAdapter(
        playbook=Playbook(),
        generator=generator,
        reflector=reflector,
        curator=curator
    )

    print("✓ All ACE components created successfully")
    return True

def main():
    """Run all tests."""
    print("Testing README Starter Example Syntax...")
    print("=" * 50)

    tests = [
        test_imports,
        test_class_creation,
        test_sample_creation,
        test_component_creation,
    ]

    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("✅ All syntax tests passed! The starter example structure is valid.")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())