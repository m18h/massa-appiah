import json
import os
import random
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Digits,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Placeholder,
    Sparkline,
    Static,
)

from src.mock_obd import mock_obd_data

METRICS_INTERVAL = int(os.getenv("DASHBOARD_METRICS_INTERVAL", 1))
QUERY_INTERVAL = int(os.getenv("DASHBOARD_QUERY_INTERVAL", 5))


# screens


class ErrorScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Go Back")]

    ERROR_TEXT = """
    An error has occurred. To continue:

    Press Enter to return to dashboard
    """

    def compose(self) -> ComposeResult:
        yield Static("Massa Appiah", id="error-title")
        yield Static(self.ERROR_TEXT)
        yield Static("Press Enter to continue [blink]_[/]", id="error-any-key")


class AboutScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Go Back")]

    def compose(self) -> ComposeResult:
        yield Placeholder("About Screen")
        yield Footer()


class QuitScreen(Screen):
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="quit-question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()


class Query(HorizontalGroup):
    """Search UI"""

    def compose(self) -> ComposeResult:
        """Create child widgets of a stopwatch."""
        yield Input(placeholder="Enter your query")
        yield Button("Query", id="query", variant="success")
        yield Button("Cancel", id="cancel", variant="error")


class QueryScreen(Screen):
    """Screen to query LLM."""

    def compose(self) -> ComposeResult:
        yield Query()
        yield Log()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        else:
            self.app.pop_screen()


# dashboard rows


class GraphRow(HorizontalGroup):
    data = reactive([])

    def compose(self) -> ComposeResult:
        yield VerticalGroup(
            Label("Speed"),
            Sparkline(self.data, summary_function=max, id="speed-graph"),
        )


class VelocityRow(HorizontalGroup):
    rpm = reactive(0.0)
    speed = reactive(0.0)
    throttle_position = reactive(0.0)
    distance = reactive(0.0)
    runtime = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield VerticalGroup(
            Label("RPM"), Digits(f"{self.rpm}", id="rpm", classes="metric-display")
        )
        yield VerticalGroup(
            Label("Speed"),
            Digits(f"{self.speed}", id="speed", classes="metric-display"),
        )
        yield VerticalGroup(
            Label("Throttle Position"),
            Digits(
                f"{self.throttle_position}",
                id="throttle_position",
                classes="metric-display",
            ),
        )
        yield VerticalGroup(
            Label("Distance"),
            Digits(f"{self.distance}", id="distance", classes="metric-display"),
        )
        yield VerticalGroup(
            Label("Runtime"),
            Digits(f"{self.runtime}", id="runtime", classes="metric-display"),
        )


class TemperatureRow(HorizontalGroup):
    coolant_temp = reactive(0.0)
    intake_temp = reactive(0.0)
    oil_temp = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield VerticalGroup(
            Label("Coolant Temp"),
            Digits(f"{self.coolant_temp}", id="coolant_temp", classes="metric-display"),
        )
        yield VerticalGroup(
            Label("Intake Temp"),
            Digits(f"{self.intake_temp}", id="intake_temp", classes="metric-display"),
        )
        yield VerticalGroup(
            Label("Oil Temp"),
            Digits(f"{self.oil_temp}", id="oil_temp", classes="metric-display"),
        )


# main app
class MessageDisplay(Static):
    message = reactive("-")

    def watch_message(self, message: str) -> None:
        self.update(f"{message}")


class MainApp(App):
    """Main App."""

    CSS_PATH = "app.tcss"
    TITLE = "Massa Appiah"
    SUB_TITLE = "Your AI Mechanic"

    random.seed(73)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield VerticalScroll(
            GraphRow(),
            VelocityRow(),
            TemperatureRow(),
            MessageDisplay(),
        )

    def on_mount(self) -> None:
        self.metrics_timer = self.set_interval(METRICS_INTERVAL, self.refresh_metrics)
        self.query_timer = self.set_interval(QUERY_INTERVAL, self.refresh_query)

    def refresh_metrics(self) -> None:
        sample_data = mock_obd_data()

        self.query_one("#rpm", Digits).update(f"{sample_data['rpm']}")
        self.query_one("#speed", Digits).update(f"{sample_data['speed']}")
        self.query_one("#throttle_position", Digits).update(
            f"{sample_data['throttle_position']}"
        )
        self.query_one("#distance", Digits).update(f"{sample_data['distance']}")
        self.query_one("#runtime", Digits).update(f"{sample_data['runtime']}")

        self.query_one("#coolant_temp", Digits).update(f"{sample_data['coolant_temp']}")
        self.query_one("#intake_temp", Digits).update(f"{sample_data['intake_temp']}")
        self.query_one("#oil_temp", Digits).update(f"{sample_data['oil_temp']}")

    def refresh_query(self) -> None:
        random.seed(73)

        self.query_one("#speed-graph", Sparkline).data = [
            random.expovariate(1 / 3) for _ in range(1000)
        ]

        message_display = self.query_one(MessageDisplay)

        message_display.message = f"{datetime.now()}"

    def action_request_quit(self) -> None:
        self.push_screen(QuitScreen())

    def action_request_query(self) -> None:
        self.push_screen(QueryScreen())

    def action_request_about(self) -> None:
        self.push_screen(AboutScreen())


if __name__ == "__main__":
    app = MainApp()
    app.run()
