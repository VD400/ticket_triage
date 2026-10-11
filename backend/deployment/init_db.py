"""Apply additive migrations and initialize checkpoints, without seeding/resetting data."""

import subprocess
import sys

from sqlalchemy import text
from database import engine


def main():
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    subprocess.run([sys.executable, "-m", "agent.setup_checkpointer"], check=True)


if __name__ == "__main__":
    main()
