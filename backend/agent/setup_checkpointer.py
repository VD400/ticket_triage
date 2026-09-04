import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

with PostgresSaver.from_conn_string(
    os.environ["DATABASE_URL"]
) as checkpointer:
    checkpointer.setup()

print("Checkpointer database initialized.")
