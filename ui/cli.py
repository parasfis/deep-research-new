"""Command-line interface for Deep Research Assistant.

This module provides a command-line interface for interacting with the research engine.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rich_print
from rich.prompt import Prompt, Confirm

from research.engine import ResearchEngine
from utils.pdf_generator import PDFGenerator
import config

logger = logging.getLogger(__name__)

# Initialize Typer app
app = typer.Typer()
console = Console()


class ResearchCLI:
    """Command-line interface for the Deep Research Assistant."""

    def __init__(self, research_engine: ResearchEngine):
        """Initialize the CLI.

        Args:
            research_engine: The research engine to use.
        """
        self.research_engine = research_engine
        self.pdf_generator = PDFGenerator()
        self.current_research = None

    def start(self):
        """Start the CLI interface."""
        self._display_welcome()
        
        while True:
            try:
                # Get research topic from user
                topic = self._get_research_topic()
                if not topic:
                    break
                    
                # Get additional context
                context = self._get_research_context()
                
                # Execute research
                self._execute_research(topic, context)
                
                # Ask if user wants to continue
                if not Confirm.ask("\nWould you like to research another topic?"):
                    break
            except KeyboardInterrupt:
                console.print("\n[yellow]Research interrupted by user.[/yellow]")
                break
            except Exception as e:
                logger.exception(f"Error in CLI: {e}")
                console.print(f"\n[red]An error occurred: {e}[/red]")
                if not Confirm.ask("Would you like to continue?"):
                    break
        
        console.print("\n[bold green]Thank you for using Deep Research Assistant![/bold green]")

    def _display_welcome(self):
        """Display welcome message."""
        console.print(Panel.fit(
            "[bold blue]Deep Research Assistant[/bold blue]\n\n"
            "A tool for performing deep research on any topic using internet sources and Ollama.",
            title="Welcome",
            border_style="blue"
        ))
        console.print("\nConnected to Ollama using model: [bold green]" + config.OLLAMA_MODEL + "[/bold green]\n")

    def _get_research_topic(self) -> Optional[str]:
        """Get research topic from user.

        Returns:
            The research topic, or None if the user wants to exit.
        """
        console.print("\n[bold]Enter your research topic:[/bold]")
        console.print("[dim](or type 'exit' to quit)[/dim]")
        topic = Prompt.ask("Topic")
        
        if topic.lower() in ["exit", "quit", "q"]:
            return None
            
        return topic

    def _get_research_context(self) -> Optional[str]:
        """Get additional context from user.

        Returns:
            Additional context for the research, or None if not provided.
        """
        console.print("\n[bold]Enter any additional context or requirements:[/bold]")
        console.print("[dim](press Enter to skip)[/dim]")
        context = Prompt.ask("Context", default="")
        
        return context if context else None

    def _execute_research(self, topic: str, context: Optional[str] = None):
        """Execute research and display results.

        Args:
            topic: The research topic.
            context: Additional context for the research.
        """
        console.print(f"\n[bold]Starting research on:[/bold] {topic}")
        if context:
            console.print(f"[bold]Context:[/bold] {context}")
        
        # Start research planning
        with console.status("[bold green]Planning research...[/bold green]") as status:
            research_plan = self.research_engine.start_research(topic, context)
        
        # Display research plan
        console.print("\n[bold]Research Plan:[/bold]")
        search_queries = research_plan.get("search_queries", [])
        subtopics = research_plan.get("subtopics", [])
        
        for i, query in enumerate(search_queries):
            console.print(f"  [bold blue]{i+1}.[/bold blue] {query}")
        
        console.print("\n[bold]Subtopics to explore:[/bold]")
        for i, subtopic in enumerate(subtopics):
            console.print(f"  [bold blue]{i+1}.[/bold blue] {subtopic}")
        
        # Execute research with progress bar
        console.print("\n[bold]Executing research...[/bold]")
        
        with Progress(
            TextColumn("[bold green]{task.description}[/bold green]"),
            BarColumn(),
            TextColumn("[bold]{task.completed}/{task.total}[/bold]"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Create a task for overall progress
            task = progress.add_task("Researching...", total=len(search_queries) + 2)  # +2 for analysis and report generation
            
            # Execute research in a separate thread to update progress
            import threading
            
            def execute_with_progress():
                self.current_research = self.research_engine.execute_research(topic, context)
                progress.update(task, completed=len(search_queries) + 2)
            
            research_thread = threading.Thread(target=execute_with_progress)
            research_thread.start()
            
            # Update progress while research is running
            while research_thread.is_alive():
                status = self.research_engine.get_research_status()
                if status.get("status") == "in_progress":
                    # Estimate progress based on time elapsed
                    elapsed = time.time() - status.get("start_time", time.time())
                    # Rough estimate: 1 query per 5 seconds + 10 seconds for analysis
                    estimated_queries_done = min(len(search_queries), int(elapsed / 5))
                    progress.update(task, completed=estimated_queries_done)
                time.sleep(0.5)
            
            research_thread.join()
        
        # Display results
        self._display_research_results(self.current_research)

    def _display_research_results(self, research_data: Dict[str, Any]):
        """Display research results.

        Args:
            research_data: Research data containing results.
        """
        if not research_data or not research_data.get("results"):
            console.print("\n[bold red]No research results available.[/bold red]")
            return
            
        results = research_data["results"]
        report = results.get("report", "No report generated.")
        analyzed_sources = results.get("analyzed_sources", [])
        
        # Display report
        console.print("\n[bold]Research Report:[/bold]")
        console.print(Panel(Markdown(report), border_style="green"))
        
        # Display sources
        console.print("\n[bold]Sources:[/bold]")
        for i, source in enumerate(analyzed_sources):
            relevance = source.get("relevance", 0)
            relevance_color = "green" if relevance >= 0.7 else "yellow" if relevance >= 0.4 else "red"
            
            console.print(f"  [bold blue]{i+1}.[/bold blue] {source.get('title', 'Untitled')}")
            console.print(f"     URL: [dim]{source.get('url', 'No URL')}[/dim]")
            console.print(f"     Relevance: [{relevance_color}]{relevance:.2f}[/{relevance_color}]")
        
        # Generate PDF report
        pdf_path = self._generate_pdf_report(research_data)
        console.print(f"\n[bold green]PDF Report generated:[/bold green] {pdf_path}")

    def _generate_pdf_report(self, research_data: Dict[str, Any]) -> str:
        """Generate a PDF report from research data.

        Args:
            research_data: Research data containing results.

        Returns:
            Path to the generated PDF file.
        """
        with console.status("[bold green]Generating PDF report...[/bold green]") as status:
            pdf_path = self.pdf_generator.generate_pdf(research_data)
        
        return pdf_path


@app.command()
def main(topic: str = typer.Option(None, help="Research topic"),
         context: str = typer.Option(None, help="Additional context for the research")):
    """Run the Deep Research Assistant from the command line."""
    # Initialize the research engine
    research_engine = ResearchEngine()
    
    # Start the CLI
    cli = ResearchCLI(research_engine)
    
    if topic:
        # Execute research with provided topic
        cli._execute_research(topic, context)
    else:
        # Start interactive CLI
        cli.start()


if __name__ == "__main__":
    app()