#!/usr/bin/env python3
"""
🌊 The Kayba Test - True Auto-Learning 🌊
==========================================
No training. Just learning from mistakes.
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rich.console import Console
from rich.panel import Panel

from ace import Generator, Reflector, Curator, Playbook
from ace import TaskEnvironment, EnvironmentResult
from ace.llm_providers import LiteLLMClient
from ace.adaptation import Sample

console = Console()


class SimpleEnvironment(TaskEnvironment):
    """Just checks if the answer is correct."""

    def evaluate(self, sample: Sample, generator_output):
        response = generator_output.final_answer.lower()

        if "no" in response and "seahorse" in response:
            return EnvironmentResult(
                feedback="✅ Correct!",
                ground_truth="No seahorse emoji exists",
                metrics={"accuracy": 1.0}
            )
        else:
            return EnvironmentResult(
                feedback="❌ Wrong. There is no seahorse emoji.",
                ground_truth="No seahorse emoji exists",
                metrics={"accuracy": 0.0}
            )


def main():
    console.print("[bold cyan]🌊 Kayba Test - Auto-Learning Demo[/bold cyan]\n")

    # Setup
    client = LiteLLMClient(model="gpt-4o", temperature=0.3, max_tokens=1000)
    generator = Generator(client)
    reflector = Reflector(client)
    curator = Curator(client)
    playbook = Playbook()
    environment = SimpleEnvironment()

    question = "Is there a seahorse emoji?"
    sample = Sample(question=question)

    # First ask
    console.print("[yellow]Round 1:[/yellow] Asking with empty playbook...")
    console.print(f"[bold]Question:[/bold] {question}")
    output1 = generator.generate(question=question, context="", playbook=playbook)
    console.print(f"[bold]Full Response:[/bold] {output1.final_answer}")
    console.print(f"[dim]Reasoning: {output1.reasoning}[/dim]")

    # Check if correct
    result1 = environment.evaluate(sample, output1)
    console.print(result1.feedback)

    # If wrong, ACE learns automatically
    if result1.metrics["accuracy"] < 1.0:
        console.print("\n[cyan]ACE is reflecting on the mistake...[/cyan]")

        # Reflect
        reflection = reflector.reflect(
            question=question,
            generator_output=output1,
            playbook=playbook,
            ground_truth=result1.ground_truth,
            feedback=result1.feedback
        )

        # Update playbook
        curator_output = curator.curate(
            reflection=reflection,
            playbook=playbook,
            question_context="emoji questions",
            progress="learning"
        )
        playbook.apply_delta(curator_output.delta)

        console.print(f"[green]Playbook updated with {len(playbook.bullets())} insights[/green]")

        # Show the playbook contents
        if len(playbook.bullets()) > 0:
            console.print("\n[cyan]📚 Current Playbook:[/cyan]")
            console.print(Panel(playbook.as_prompt(), style="cyan"))

    # Second ask - should use playbook
    console.print(f"\n[yellow]Round 2:[/yellow] Asking again with {len(playbook.bullets())} learned insights...")
    console.print(f"[bold]Question:[/bold] {question}")
    output2 = generator.generate(question=question, context="", playbook=playbook)
    console.print(f"[bold]Full Response:[/bold] {output2.final_answer}")
    console.print(f"[dim]Reasoning: {output2.reasoning}[/dim]")
    if output2.bullet_ids:
        console.print(f"[dim]Used bullets: {output2.bullet_ids}[/dim]")

    # Check if correct now
    result2 = environment.evaluate(sample, output2)
    console.print(result2.feedback)

    if result2.metrics["accuracy"] > result1.metrics["accuracy"]:
        console.print("\n[bold green]✅ ACE learned from its mistake![/bold green]")
    else:
        console.print("\n[yellow]ACE needs more examples to learn this fact.[/yellow]")


if __name__ == "__main__":
    main()