from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
load_dotenv()

engine = create_engine(os.getenv("READONLY_DB_URL"))
readonly_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

