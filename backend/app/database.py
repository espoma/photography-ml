import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()

# 2. Get the Database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file")

# 3. Create the Database Engine
# echo=True means it will print every SQL query to the terminal (great for debugging)
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    """Dependency function to give a fresh database session to each request."""
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """Creates all tables defined in your SQLModel classes."""
    SQLModel.metadata.create_all(engine)
