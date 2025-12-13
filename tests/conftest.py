"""
Pytest Configuration and Fixtures

Общие fixtures для всех тестов.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from app.core.container import Container, reset_container


@pytest.fixture(autouse=True)
def reset_di():
    """Сбрасываем DI контейнер перед каждым тестом."""
    reset_container()
    yield
    reset_container()


@pytest.fixture
def test_container():
    """Тестовый DI контейнер."""
    return Container()


@pytest.fixture
def mock_repository():
    """Mock для RepositoryFacade."""
    repo = Mock()
    repo.channels = Mock()
    repo.posts = Mock()
    repo.keywords = Mock()
    repo.analytics = Mock()
    return repo


@pytest.fixture
def mock_logger():
    """Mock для logger."""
    return Mock()


@pytest.fixture
def sample_channel_data():
    """Пример данных канала."""
    return {
        "id": -1002508742544,
        "username": "technews",
        "title": "Tech News",
        "about": "Latest technology news",
        "participants_count": 10000
    }


@pytest.fixture
def sample_posts_data():
    """Пример данных постов."""
    from datetime import datetime
    
    return [
        {
            "date": datetime.utcnow(),
            "views": 100,
            "forwards": 5,
            "text": "Test post 1"
        },
        {
            "date": datetime.utcnow(),
            "views": 200,
            "forwards": 10,
            "text": "Test post 2 with @channel1 mention"
        },
        {
            "date": datetime.utcnow(),
            "views": 150,
            "forwards": 7,
            "text": "Test post 3 t.me/channel2"
        },
    ]


@pytest.fixture
def sample_analysis_result():
    """Пример результата анализа."""
    return {
        "audience": "IT specialists 25-40",
        "keywords": ["python", "django", "backend"],
        "tone": "Professional"
    }

