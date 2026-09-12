import os
from dotenv import load_dotenv

load_dotenv(".env.test")

os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("COHERE_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.base import Base
from models.user import User, UserRole
from auth.security import hash_password
from auth.jwtToken import create_access_token

TEST_DB_URL = os.environ["TEST_DATABASE_URL"] 
engine = create_engine(TEST_DB_URL)
TestSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    
@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()
    

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    
@pytest.fixture
def make_user(db_session):
    def _make(role=UserRole.AGENT, username="agent1"):
        user = User(
            username=username,
            email=f"{username}@test.com",
            hashed_password=hash_password("password123"),
            role=role
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _make


@pytest.fixture
def auth_headers(make_user):
    def _headers(role=UserRole.AGENT):
        user = make_user(
            role=role,
            username=f"{role.value}_user"
        )

        token = create_access_token({
            "sub": str(user.id),
            "role": role.value
        })

        return {
            "Authorization": f"Bearer {token}"
        }

    return _headers



        

