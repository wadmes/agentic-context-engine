#!/usr/bin/env python3
"""
🌊 The Kayba Test - Self-Learning Demo 🌊
==========================================
Watch ACE learn from its mistakes in real-time!

This demo shows how ACE automatically learns from feedback
without any explicit training - just like humans do.
"""

import time
import os
from typing import Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.text import Text
from rich.columns import Columns

# ACE imports
from ace import Generator, Reflector, Curator
from ace import TaskEnvironment, EnvironmentResult, Playbook
from ace.llm_providers import LiteLLMClient
from ace.adaptation import Sample

console = Console()


def print_kayba_logo():
    """Display the Kayba logo."""
    logo = """
    🌊 The Kayba Test: Self-Learning Demo 🌊
           Can AI learn from one mistake?

         Watch ACE remember what it learns!
    """
    console.print(Panel(logo, style="cyan bold", title="[white]Kayba AI[/white]"))
    time.sleep(1)


class InteractiveFeedbackEnvironment(TaskEnvironment):
    """Environment that provides feedback based on correctness."""

    def __init__(self, correct_answer: str):
        self.correct_answer = correct_answer.lower()

    def evaluate(self, sample: Sample, generator_output):
        """Evaluate the response and provide feedback."""
        response = generator_output.final_answer.lower()

        # Check if the response is correct
        if "no" in response and "seahorse emoji" in response:
            feedback = "✅ Correct! There is indeed no seahorse emoji in Unicode."
            accuracy = 1.0
        elif "yes" in response or "🐠" in response or "🐉" in response or "🦄" in response:
            feedback = "❌ Wrong! That's not a seahorse. There is no seahorse emoji in Unicode."
            accuracy = 0.0
        else:
            feedback = "⚠️ Unclear response. The correct answer is: there is no seahorse emoji."
            accuracy = 0.5

        return EnvironmentResult(
            feedback=feedback,
            ground_truth=self.correct_answer,
            metrics={
                "accuracy": accuracy,
                "response_length": len(response.split())
            }
        )


def run_self_learning_demo():
    """Run the self-learning demonstration."""

    print_kayba_logo()

    # Initialize components
    console.print("[cyan]Initializing ACE components...[/cyan]")

    model = "gpt-3.5-turbo" if os.getenv("OPENAI_API_KEY") else "claude-3-haiku-20240307"
    client = LiteLLMClient(model=model, temperature=0.7, max_tokens=500)

    generator = Generator(client)
    reflector = Reflector(client)
    curator = Curator(client)
    playbook = Playbook()  # Start with empty playbook

    environment = InteractiveFeedbackEnvironment(
        correct_answer="No, there is no seahorse emoji in Unicode"
    )

    # The question we'll ask twice
    question = "Is there a seahorse emoji?"
    context = "Please give a direct yes or no answer. Be specific about seahorse emoji existence in Unicode."

    console.print("\n[bold yellow]═══════════════════════════════════════════════[/bold yellow]")
    console.print("[bold white]ROUND 1: First Encounter (No Prior Knowledge)[/bold white]")
    console.print("[bold yellow]═══════════════════════════════════════════════[/bold yellow]\n")

    # First ask - ACE has no knowledge
    console.print(f"[bold cyan]Question:[/bold cyan] {question}")
    console.print("[dim]ACE has no prior knowledge about this...[/dim]\n")

    # Generate first response
    with console.status("[cyan]ACE is thinking...[/cyan]"):
        first_output = generator.generate(
            question=question,
            context=context,
            playbook=playbook  # Empty playbook
        )

    # Display first response
    first_response_panel = Panel(
        first_output.final_answer,
        title="[red]ACE's First Response[/red]",
        style="red",
        subtitle=f"[dim]{len(first_output.final_answer.split())} tokens[/dim]"
    )
    console.print(first_response_panel)

    # Evaluate the response
    sample = Sample(question=question, context=context)
    env_result = environment.evaluate(sample, first_output)

    # Show feedback
    feedback_panel = Panel(
        env_result.feedback,
        title="[yellow]Feedback[/yellow]",
        style="yellow" if env_result.metrics["accuracy"] < 1 else "green"
    )
    console.print(feedback_panel)

    # If ACE got it wrong, show the learning process
    if env_result.metrics["accuracy"] < 1.0:
        console.print("\n[bold cyan]⚙️  ACE is learning from this feedback...[/bold cyan]")

        # Reflection phase
        with Progress() as progress:
            task = progress.add_task("[cyan]Reflecting on the mistake...", total=3)

            # Provide more specific context for learning
            enhanced_question = f"{question} (Context: Unicode emoji standards)"

            reflection = reflector.reflect(
                question=enhanced_question,
                generator_output=first_output,
                playbook=playbook,
                ground_truth="No, there is no seahorse emoji in Unicode",
                feedback=f"{env_result.feedback} Remember: There is NO seahorse emoji in Unicode standards."
            )
            progress.update(task, advance=1)
            time.sleep(0.5)

            # Show what ACE learned
            if reflection.key_insight:
                console.print(f"[yellow]💡 Insight:[/yellow] {reflection.key_insight}")
            progress.update(task, advance=1)
            time.sleep(0.5)

            # Curator updates the playbook
            curator_output = curator.curate(
                reflection=reflection,
                playbook=playbook,
                question_context="Emoji existence questions",
                progress="Learning from feedback"
            )
            progress.update(task, advance=1)

            # Apply the updates
            playbook.apply_delta(curator_output.delta)

        # Show playbook update
        if len(playbook.bullets()) > 0:
            console.print(f"\n[green]✅ Playbook updated with {len(playbook.bullets())} new insight(s)![/green]")

            # Display the new knowledge
            playbook_content = Panel(
                playbook.as_prompt(),
                title="[green]📚 ACE's Updated Knowledge[/green]",
                style="green"
            )
            console.print(playbook_content)

    # Wait a moment before second round
    console.print("\n[dim]Let's ask the same question again...[/dim]")
    time.sleep(2)

    console.print("\n[bold green]═══════════════════════════════════════════════[/bold green]")
    console.print("[bold white]ROUND 2: Testing Memory (Using Learned Knowledge)[/bold white]")
    console.print("[bold green]═══════════════════════════════════════════════[/bold green]\n")

    # Second ask - ACE now has knowledge in its playbook
    console.print(f"[bold cyan]Question:[/bold cyan] {question}")
    console.print(f"[dim]ACE now has {len(playbook.bullets())} insight(s) in its playbook...[/dim]\n")

    # Generate second response using the updated playbook
    with console.status("[cyan]ACE is recalling what it learned...[/cyan]"):
        second_output = generator.generate(
            question=question,
            context=context,
            playbook=playbook  # Now contains learned knowledge
        )

    # Display second response
    second_response_panel = Panel(
        second_output.final_answer,
        title="[green]ACE's Second Response (Using Playbook)[/green]",
        style="green",
        subtitle=f"[dim]{len(second_output.final_answer.split())} tokens | Used bullets: {second_output.bullet_ids}[/dim]"
    )
    console.print(second_response_panel)

    # Evaluate the second response
    env_result_2 = environment.evaluate(sample, second_output)

    # Show feedback
    feedback_panel_2 = Panel(
        env_result_2.feedback,
        title="[green]Feedback[/green]",
        style="green" if env_result_2.metrics["accuracy"] == 1 else "yellow"
    )
    console.print(feedback_panel_2)

    # Show improvement metrics
    console.print("\n[bold cyan]📊 Learning Metrics[/bold cyan]")

    metrics_table = Table(show_header=True, title="Before vs After Learning")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("First Ask", style="red")
    metrics_table.add_column("Second Ask", style="green")
    metrics_table.add_column("Improvement", style="yellow")

    # Accuracy
    acc1 = env_result.metrics["accuracy"]
    acc2 = env_result_2.metrics["accuracy"]
    metrics_table.add_row(
        "Accuracy",
        f"{acc1:.0%}",
        f"{acc2:.0%}",
        f"↑ {(acc2-acc1):.0%}" if acc2 > acc1 else "Same"
    )

    # Response length
    len1 = len(first_output.final_answer.split())
    len2 = len(second_output.final_answer.split())
    metrics_table.add_row(
        "Response Length",
        f"{len1} tokens",
        f"{len2} tokens",
        f"↓ {((len1-len2)/len1*100):.0f}%" if len2 < len1 else "Same"
    )

    # Playbook usage
    metrics_table.add_row(
        "Used Playbook",
        "No (empty)",
        f"Yes ({len(second_output.bullet_ids)} bullets)",
        "✅ Learned!"
    )

    console.print(metrics_table)

    # Final message
    if acc2 > acc1:
        success_msg = """
        🎉 SUCCESS! ACE learned from just ONE correction!

        This demonstrates the power of ACE:
        • ❌ First ask: Got it wrong (no prior knowledge)
        • 🧠 Automatic learning: Reflected and updated playbook
        • ✅ Second ask: Got it right (used learned knowledge)

        Just like humans, ACE remembers its lessons!
        """
        console.print(Panel(success_msg, style="bold green", title="[bold]The Kayba Test: PASSED![/bold]"))

    # Save the playbook
    console.print("\n[cyan]Saving learned knowledge to 'kayba_learned.json'...[/cyan]")
    playbook.save_to_file("kayba_learned.json")
    console.print("[green]✅ Playbook saved! ACE will remember this lesson.[/green]")


def main():
    """Main entry point."""
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[yellow]No API key found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY[/yellow]")
        return

    try:
        run_self_learning_demo()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()