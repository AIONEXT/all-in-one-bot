# AIO Bot - All-In-One Desktop Intelligence System

A **fully automated, AI-driven master mind** for comprehensive system management. A single desktop bot that monitors every aspect of your machine, learns your habits, auto-maintains your system, and keeps everything ready and updated across Windows, macOS, and Linux.

## Overview

AIO Bot is a comprehensive system intelligence platform that combines:

- **Live System Monitoring** - CPU, RAM, Disk, Network, GPU, Processes, Temperatures
- **AI Habit Learning** - Pattern recognition, predictive scheduling, behavior analysis
- **Smart File Management** - Auto-organization, duplicate detection, cleanup, backups
- **Health Monitoring** - Service monitoring, SMART disk health, system logs, update tracking
- **Auto-Healing** - Self-maintenance, service restart, temp cleanup, auto-updates
- **Cross-Platform GUI** - Native desktop app for Windows, macOS, and Linux
- **Security First** - Local-first data, encryption, audit logging, permission management

## Features

### System Monitoring
- Real-time CPU, memory, disk, network, and GPU metrics
- Per-core CPU usage, frequency monitoring, load averages
- Process tracking with top consumers
- SMART disk health monitoring (reallocated sectors, temperature, power-on hours)
- Cross-platform: Windows (WMI), macOS (powermetrics), Linux (/proc, sysfs)

### AI-Driven Habit Learning
- Temporal pattern detection (hourly, daily, weekly)
- Application usage pattern recognition
- Sequence prediction (A followed by B)
- Predictive task scheduling based on learned habits
- Privacy-first: local-only processing with optional anonymization
- Model persistence and automatic retraining

### File & Data Management
- Smart file categorization (Documents, Images, Videos, Code, etc.)
- Duplicate detection by content hash (SHA-256)
- Automated cleanup of temp files, old downloads, large unused files
- Configurable organization rules with custom extensions
- Automated backups with retention policies

### System Health Monitoring
- Service/daemon monitoring with auto-restart for critical services
- Windows Event Logs, macOS Unified Logs, Linux journalctl parsing
- SMART disk health with predictive failure detection
- System update checking (Windows Update, macOS softwareupdate, apt/dnf/pacman)
- Critical alert threshold configuration

### Automation & Self-Healing
- Priority-based task queue with retry logic
- Cron-style scheduling with maintenance windows
- Predictive task scheduling from habit engine
- Auto-fix for common issues (high CPU, memory, disk)
- Configurable maintenance windows (default 2-4 AM)

### Cross-Platform Desktop GUI
- Native PySide6/Qt interface
- Real-time dashboard with metric cards
- Detailed system monitor (CPU, Memory, Disk, Network, GPU, Processes)
- Health overview with service status and disk health
- Learning insights with patterns and predictions
- File management with duplicate cleanup
- Automation task scheduler and history
- Comprehensive settings panel

### Security & Privacy
- Local-first architecture (no cloud required)
- AES-256 encryption for sensitive data at rest
- API key management with rotation
- Audit logging for all security events
- Rate limiting and account lockout protection
- Data classification (Public/Internal/Confidential/Restricted)

## Architecture

```
+-------------------------------------------------------------+
|                      AIO Bot Core                            |
+-------------------------------------------------------------+
  +--------------+  +--------------+  +--------------+       
  |  Monitoring  |  |   Learning   |  | Data Mgmt    |       
  |  (psutil,    |  |  (Pattern    |  |  (Organize,  |       
  |   GPUtil,    |  |   Detection, |  |   Dedup,     |       
  |   Platform)  |  |   Prediction)|  |   Backup)    |       
  +------+-------+  +------+-------+  +------+-------+       
         |                 |                 |                 
         +-----------------+-----------------+                 
                           |                                   
              +------------+------------+                       
              |    Task Runner &       |                       
              |    Scheduler           |                       
              |  (Auto-fix, Cron,      |                       
              |   Maintenance)         |                       
              +-----------+------------+                       
                          |                                     
         +----------------+----------------+                     
         |                |                |                     
   +----------+   +--------------+  +--------------+          
   | Security |   |   Health     |  |    GUI       |          
   | Manager  |   |  Monitor     |  | (PySide6)    |          
   +----------+   +--------------+  +--------------+          
```

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/all-in-one-bot.git
cd all-in-one-bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the GUI application
python run_bot.py
```

### Building Standalone Executable (Windows)

```bash
# Install build dependencies
pip install -r requirements-build.txt

# Build the executable
python build_exe.py

# Run the bundled app
dist\AllInOneBot\AllInOneBot.exe
```

### Running with Docker

```bash
# Build and start the backend
docker compose up --build -d
```

## Configuration

Configuration is stored in:
- **Windows**: `%LOCALAPPDATA%\AIOBot\config.json`
- **macOS/Linux**: `~/.config/AIOBot/config.json`

Key configuration sections:
- `monitoring` - Intervals, thresholds, component enables
- `learning` - Model updates, detection window, privacy mode
- `data_mgmt` - Organization rules, cleanup, backup settings
- `health` - Check intervals, log sources, SMART monitoring
- `automation` - Maintenance window, auto-fix settings
- `security` - Encryption, auth, audit logging
- `gui` - Theme, language, refresh rates

## Project Structure

```
all-in-one-bot/
├── aio_bot/                    # Core AIO Bot modules
│   ├── core/                   # Main bot orchestration
│   ├── config/                 # Configuration management
│   ├── monitoring/             # System monitoring
│   ├── learning/               # Habit learning engine
│   ├── data_mgmt/              # File organization
│   ├── health/                 # Health monitoring
│   ├── automation/             # Task runner & scheduler
│   ├── security/               # Security manager
│   └── gui/                    # PySide6 desktop GUI
├── backend/                    # FastAPI backend (legacy)
├── client/                     # Example client (legacy)
├── run_bot.py                  # Main entry point
├── build_exe.py                # PyInstaller build script
├── requirements.txt            # Runtime dependencies
└── requirements-build.txt      # Build dependencies
```

## Development

### Code Style
```bash
# Linting
ruff check .

# Type checking
mypy .

# Format
ruff format .
```

### Running Tests
```bash
pytest tests/
```

## Platform Support

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| System Monitoring | Yes | Yes | Yes |
| GPU Monitoring | Yes | Yes | Yes |
| SMART Disk Health | Yes | Yes | Yes |
| Service Monitoring | Yes | Yes | Yes |
| Event Logs | Yes | Yes | Yes |
| Update Checking | Yes | Yes | Yes |
| Native GUI | Yes | Yes | Yes |
| Auto-start | Yes | Yes | Yes |
| Packaging | EXE/MSI | DMG | AppImage/deb/rpm |

## Security Considerations

- All data processed locally by default
- Encryption keys generated per-installation
- No telemetry without explicit consent
- Audit log for all administrative actions
- API keys hashed with SHA-256 before storage
- Secure file deletion for sensitive data

## License

MIT License - see the `LICENSE` file for details.

## Contributing

Contributions are welcome! Fork the repo, create a feature branch, and open a PR. Please ensure the CI pipeline passes before submitting.

---

**Happy system management!**