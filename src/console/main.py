import os
import sys
import inquirer

from inquirer.themes import GreenPassion
from art import text2art
from colorama import Fore

from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text
from data.config import API_ID, API_HASH, STICKER_NAME, COUNT_FOR_BUY_TON, COUNT_FOR_BUY_STARS

sys.path.append(os.path.realpath("."))


class Console:
    MODULES = [
        "🔑 Create session",
        "🎯 Start sniping",
        "💰 Buy with your data"
    ]

    def __init__(self):
        self.rich_console = RichConsole()

    def show_dev_info(self):
        os.system("cls" if os.name == "nt" else "clear")

        title = text2art("Sticker BOT")
        styled_title = Text(title, style="bold cyan")

        # Создаем более яркий и заметный стиль для ссылок
        telegram = Text("Dev Channel: https://t.me/vzhuh333",
                        style="bold bright_red blink")

        dev_panel = Panel(
            Text.assemble(styled_title, "\n\n", telegram, "\n", telegram, "\n", telegram),
            border_style="bright_yellow",
            padding=(1, 2),
            title="[bold red blink]Sticker BOT[/bold red blink]",
            expand=False,
        )

        self.rich_console.print(dev_panel)
        print()

    @staticmethod
    def prompt(data: list):
        answers = inquirer.prompt(data, theme=GreenPassion())
        return answers

    def display_config(self):
        config = Table(title="Config Overview",
                       box=box.ROUNDED, show_lines=True)
        config.add_column("Parameter", style="cyan")
        config.add_column("Value", style="magenta")
        config.add_row("API ID", f"{str(API_ID)[:5]}...{str(API_ID)[-5:]}")
        config.add_row(
            "API Hash", f"{str(API_HASH)[:5]}...{str(API_HASH)[-5:]}")
        config.add_row("[bold underline]Count for buy ton[/bold underline]", str(COUNT_FOR_BUY_TON))
        config.add_row("[bold underline]Count for buy stars[/bold underline]", str(COUNT_FOR_BUY_STARS))
        config.add_row("[bold underline]Sticker name[/bold underline]", STICKER_NAME)

        panel = Panel(
            config,
            expand=False,
            border_style="green",
            subtitle="[italic]Use arrow keys to navigate[/italic]",
        )
        self.rich_console.print(panel)

    def get_module(self):
        questions = [
            inquirer.List(
                "module",
                message=Fore.LIGHTBLACK_EX + "Select the module",
                choices=self.MODULES,
            ),
        ]

        answers = self.prompt(questions)
        return answers.get("module")

    def build(self) -> str:
        self.show_dev_info()
        self.display_config()

        module = self.get_module()
        return module
