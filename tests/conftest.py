"""Pytest configuration for multi-agent tests."""
import pytest
import shutil
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def clean_database():
    """Clean the CAD database before test session starts."""
    # Remove database directory to ensure clean state
    db_dir = Path("data/workspaces/main")
    if db_dir.exists():
        shutil.rmtree(db_dir)
    
    yield
    
    # Cleanup after tests (optional - comment out to inspect database state)
    # if db_dir.exists():
    #     shutil.rmtree(db_dir)


@pytest.fixture(scope="function", autouse=True)
def reset_database_per_test():
    """Reset database before each test to prevent UNIQUE constraint violations."""
    db_dir = Path("data/workspaces/main")
    if db_dir.exists():
        shutil.rmtree(db_dir)
    
    yield
