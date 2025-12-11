# Contributing to Hybrid Search RAG

Thank you for your interest in contributing to the Hybrid Search RAG project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We pledge to:

- Be respectful and inclusive
- Welcome diverse perspectives
- Focus on what is best for the community
- Show empathy towards other community members

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

**Unacceptable behavior includes:**
- Harassment, trolling, or discriminatory comments
- Publishing others' private information
- Other conduct that could reasonably be considered inappropriate

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.12 or higher
- UV package manager
- Docker and Docker Compose
- Git
- A GitHub account

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/hybrid-search-rag.git
   cd hybrid-search-rag
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/yourusername/hybrid-search-rag.git
   ```

## Development Setup

### 1. Install Dependencies

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys (for testing)
nano .env
```

### 3. Start Local Services

```bash
# Start Qdrant, Elasticsearch, Redis
docker-compose -f docker/docker-compose.yml up -d
```

### 4. Run Tests

```bash
# Run all tests to verify setup
pytest

# With coverage
pytest --cov=src
```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

1. **Bug Fixes**: Fix issues identified in the issue tracker
2. **Features**: Implement new features from the roadmap
3. **Documentation**: Improve or add documentation
4. **Tests**: Add or improve test coverage
5. **Performance**: Optimize existing code
6. **Examples**: Add usage examples or tutorials

### Finding Issues

- Check the [issue tracker](https://github.com/yourusername/hybrid-search-rag/issues)
- Look for issues labeled `good first issue` or `help wanted`
- Comment on an issue to indicate you're working on it

### Creating Issues

Before creating a new issue:

1. **Search existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Provide clear descriptions** with:
   - What you expected to happen
   - What actually happened
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)
   - Relevant logs or error messages

## Pull Request Process

### 1. Create a Branch

Create a feature branch from `main`:

```bash
# Update your local main
git checkout main
git pull upstream main

# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes
- `perf/` - Performance improvements

### 2. Make Changes

Follow these guidelines while making changes:

- Write clean, readable code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed
- Keep commits atomic and focused

### 3. Commit Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: brief description

Detailed explanation of what changed and why.

Fixes #123"
```

**Commit message format:**
- Use present tense ("Add feature" not "Added feature")
- First line: brief summary (50 chars or less)
- Blank line
- Detailed description if needed
- Reference related issues

### 4. Run Tests and Linting

Before pushing, ensure all checks pass:

```bash
# Run tests
pytest

# Check code formatting
ruff format src/ tests/

# Check linting
ruff check src/ tests/

# Type checking
mypy src/

# Fix auto-fixable issues
ruff check src/ tests/ --fix
```

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub:

1. Go to your fork on GitHub
2. Click "Pull Request"
3. Select your branch
4. Fill out the PR template
5. Link related issues
6. Request review

### 6. PR Review Process

- **CI Checks**: All tests must pass
- **Code Review**: At least one approval required
- **Documentation**: Update docs if needed
- **Changelog**: Update if applicable

**Responding to feedback:**
- Be respectful and open to suggestions
- Make requested changes in new commits
- Respond to all comments
- Mark conversations as resolved when addressed

### 7. After Merge

After your PR is merged:

```bash
# Update your local main
git checkout main
git pull upstream main

# Delete feature branch
git branch -d feature/your-feature-name

# Delete remote branch
git push origin --delete feature/your-feature-name
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings
- **Imports**: Organized (standard, third-party, local)

### Code Formatting

We use **Ruff** for formatting and linting:

```bash
# Format code
ruff format .

# Check formatting
ruff format --check .

# Lint code
ruff check .

# Auto-fix issues
ruff check . --fix
```

### Type Hints

Use type hints for all functions:

```python
def process_document(
    document_id: str,
    chunking_strategy: str = "semantic"
) -> dict[str, Any]:
    """Process and index a document.

    Args:
        document_id: Unique document identifier
        chunking_strategy: Strategy for chunking

    Returns:
        Processing result with status

    Raises:
        ValueError: If document_id is invalid
    """
    ...
```

### Docstrings

Use Google-style docstrings:

```python
class DocumentProcessor:
    """Process documents for indexing.

    This class handles document parsing, chunking, and embedding
    generation for the RAG system.

    Attributes:
        parser: Document parser instance
        chunker: Chunking strategy instance

    Example:
        >>> processor = DocumentProcessor()
        >>> result = processor.process("doc_123")
    """

    def process(self, document_id: str) -> dict:
        """Process a document.

        Args:
            document_id: Document to process

        Returns:
            Processing result
        """
        ...
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
├── integration/       # Integration tests (external services)
└── load/             # Load/performance tests
```

### Writing Tests

Use **pytest** for all tests:

```python
import pytest
from src.embeddings.bge_embedder import BGEEmbedder


class TestBGEEmbedder:
    """Tests for BGE embedder."""

    @pytest.fixture
    def embedder(self):
        """Create embedder instance."""
        return BGEEmbedder()

    def test_embed_single_text(self, embedder):
        """Test embedding generation for single text."""
        text = "This is a test sentence."
        embedding = embedder.embed(text)

        assert embedding is not None
        assert len(embedding) == 768  # BGE dimensions
        assert all(-1 <= x <= 1 for x in embedding)

    def test_embed_batch(self, embedder):
        """Test batch embedding generation."""
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = embedder.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 768 for e in embeddings)

    @pytest.mark.parametrize("text,expected_dim", [
        ("Short", 768),
        ("A longer text with more words", 768),
    ])
    def test_embedding_dimensions(self, embedder, text, expected_dim):
        """Test embedding dimensions for various inputs."""
        embedding = embedder.embed(text)
        assert len(embedding) == expected_dim
```

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/unit/
pytest tests/integration/

# Specific file
pytest tests/unit/test_embeddings.py

# Specific test
pytest tests/unit/test_embeddings.py::TestBGEEmbedder::test_embed_single_text

# With coverage
pytest --cov=src --cov-report=html

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only failed tests
pytest --lf
```

### Test Coverage

- **Aim for 80%+ coverage**
- All new features must include tests
- Test both success and failure cases
- Test edge cases

Check coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

## Documentation

### Code Documentation

- Add docstrings to all public functions/classes
- Use type hints
- Include usage examples
- Document exceptions

### Documentation Files

Update relevant documentation:

- `README.md` - Overview and quick start
- `docs/API.md` - API endpoint reference
- `docs/*.md` - Other guides
- `CONTRIBUTING.md` - This file

### Building Documentation

```bash
# Install documentation tools
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build
mkdocs build
```

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions

### Getting Help

If you need help:

1. Check existing documentation
2. Search closed issues
3. Ask in GitHub Discussions
4. Create a new issue if needed

### Recognition

Contributors will be:

- Listed in the Contributors section
- Mentioned in release notes for significant contributions
- Thanked in project documentation

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag -a v1.2.3 -m "Release v1.2.3"`
4. Push tag: `git push origin v1.2.3`
5. GitHub Actions will build and deploy
6. Create GitHub release with notes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing:

- Check this guide
- Ask in GitHub Discussions
- Create an issue labeled `question`
- Contact maintainers at: contributing@example.com

---

Thank you for contributing to Hybrid Search RAG! 🎉
