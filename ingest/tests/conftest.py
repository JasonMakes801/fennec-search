"""
Pytest fixtures for ingest tests.

IMPORTANT: Always run tests with docker-compose.test.yml to use isolated DB:
    docker compose -f docker-compose.test.yml run --rm test
"""

import os
import pytest
import psycopg2
from pathlib import Path

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def get_test_db_connection():
    """Get connection to test database."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "fennec_test"),
        user=os.environ.get("DB_USER", "fennec_test"),
        password=os.environ.get("DB_PASSWORD", "fennec_test")
    )


@pytest.fixture(scope="session")
def db_connection():
    """
    Database connection for tests.
    Uses test database (fennec_test), NOT production.
    """
    conn = get_test_db_connection()
    
    # Safety check - refuse to run on production database
    db_name = os.environ.get("DB_NAME", "fennec_test")
    if db_name == "fennec" and os.environ.get("ALLOW_PROD_TESTS") != "true":
        conn.close()
        raise RuntimeError(
            "Refusing to run tests on production database 'fennec'. "
            "Use docker-compose.test.yml for isolated test runs."
        )
    
    yield conn
    conn.close()


@pytest.fixture
def clean_db(db_connection):
    """
    Clean database state before AND after each test.
    Ensures tests are isolated from each other.
    """
    def _clean():
        cur = db_connection.cursor()
        cur.execute("DELETE FROM faces")
        cur.execute("DELETE FROM scenes")
        cur.execute("DELETE FROM enrichment_queue")
        cur.execute("DELETE FROM files")
        db_connection.commit()
        cur.close()
    
    # Clean before test
    _clean()
    
    yield db_connection
    
    # Clean after test (ensures no leftover data)
    _clean()


@pytest.fixture
def test_video_normal():
    """Path to normal test video with audio."""
    return str(FIXTURES_DIR / "test_normal.mp4")


@pytest.fixture
def test_video_no_audio():
    """Path to test video without audio track."""
    return str(FIXTURES_DIR / "test_no_audio.mp4")


@pytest.fixture
def test_video_multi_scene():
    """Path to test video with multiple scenes."""
    return str(FIXTURES_DIR / "test_multi_scene.mp4")


@pytest.fixture
def test_video_corrupted():
    """Path to corrupted/truncated video file."""
    return str(FIXTURES_DIR / "test_corrupted.mp4")


@pytest.fixture
def temp_watch_folder(tmp_path):
    """
    Create a temporary watch folder for testing.
    Returns path and cleans up after test.
    """
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    return str(watch_dir)
