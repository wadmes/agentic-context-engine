#!/usr/bin/env python3
"""Test script for the README starter example."""

import os
from ace import (
    OfflineAdapter, Generator, Reflector, Curator,
    LiteLLMClient, DummyLLMClient, Sample, TaskEnvironment, EnvironmentResult, Playbook
)

# Initialize with any LLM
# Use DummyLLMClient if no API key is set
if os.getenv("OPENAI_API_KEY"):
    client = LiteLLMClient(model="gpt-4o-mini")
else:
    print("No OPENAI_API_KEY found, using DummyLLMClient for testing")
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

# Create training samples
samples = [
    Sample(question="What is 2+2?", ground_truth="4"),
    Sample(question="What is 5*3?", ground_truth="15")
]

# Train the agent
environment = MathEnvironment()
results = adapter.run(samples, environment, epochs=1)

# Now use the trained agent
result = adapter.generator.generate(
    question="What is 7*8?",
    context=None,
    playbook=adapter.playbook
)
print(result.final_answer)  # Agent applies learned strategies