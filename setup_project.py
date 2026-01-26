"""Development and setup utilities for PyParrot."""

from pathlib import Path


def setup_project():
    """Initialize project directories and files."""
    project_root = Path(__file__).parent

    # Create necessary directories
    dirs = [
        project_root / "data" / "models",
        project_root / "data" / "datasets",
        project_root / "output" / "logs",
        project_root / "output" / "models",
    ]

    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")


if __name__ == "__main__":
    setup_project()
