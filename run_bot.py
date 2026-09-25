#!/usr/bin/env python3
"""
AIO Bot - All-In-One Desktop Intelligence System
Main entry point for the application.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from aio_bot.core.bot import AIOBot
from aio_bot.gui.app import run_gui_app


def setup_logging():
    """Setup application logging."""
    log_dir = Path.home() / '.aiobot' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'aiobot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


async def main():
    """Main async entry point."""
    setup_logging()
    logger = logging.getLogger("AIOBot.Main")

    logger.info("Starting AIO Bot v2.0.0")

    # Create bot instance
    bot = AIOBot()

    # Setup signal handlers
    loop = asyncio.get_running_loop()

    def shutdown_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(bot.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    # Run GUI application
    try:
        exit_code = await run_gui_app(bot)
        return exit_code
    except Exception as e:
        logger.error("Application error: %s", e, exc_info=True)
        return 1
    finally:
        logger.info("AIO Bot stopped")


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nShutdown requested")
        sys.exit(0)
