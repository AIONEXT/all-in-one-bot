"""
AIO Bot GUI Application Entry Point.
"""

import asyncio
import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from aio_bot.core.bot import AIOBot
from aio_bot.gui.main_window import MainWindow


def setup_logging():
    """Setup application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def run_gui_app(bot: AIOBot):
    """Run the GUI application with the bot."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(bot.config.app_name)
    app.setApplicationVersion(bot.config.version)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Create and show main window
    window = MainWindow(bot)

    if bot.config.gui.start_minimized:
        window.hide()
    else:
        window.show()

    # Initialize and start bot
    if await bot.initialize():
        await bot.start()

        # Run Qt event loop
        # We need to integrate asyncio with Qt
        loop = asyncio.get_event_loop()

        # Create a timer to process asyncio events
        timer = QTimer()
        timer.setInterval(100)  # 100ms
        timer.timeout.connect(lambda: None)  # Keep event loop alive
        timer.start()

        # Run the app
        return app.exec()
    else:
        logging.error("Failed to initialize bot")
        return 1
