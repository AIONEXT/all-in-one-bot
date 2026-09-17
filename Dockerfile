# Use a slim Python image for a small attack surface.
FROM python:3.12-slim

# Create a non‑root user to run the app.
RUN useradd -m appuser
WORKDIR /app

# Install runtime dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code.
COPY backend ./backend
COPY client ./client

# Switch to non‑root user.
USER appuser

EXPOSE 8000

# Command to start the FastAPI server.
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
