from textual.widgets import Static # Using Static for potentially more complex content

class WelcomeWidget(Static):
    def __init__(self):
        super().__init__("Welcome to TUIDE!\n\nSelect a file from the explorer to begin.\nOr use Ctrl+P for commands (soon!).")
        # self.styles.text_align = "center" # Can be done via CSS too for Static
        # For Static, content-align in CSS is preferred for centering.
