# Contributing to PostBot 🤝

Thank you for your interest in contributing to PostBot! This document provides guidelines and information for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## 🤝 Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- **Be respectful** to all contributors and users
- **Be inclusive** and welcoming to newcomers
- **Be constructive** in feedback and discussions
- **Focus on the project** and avoid personal attacks
- **Help others learn** and grow in the community

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- MongoDB database
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Git for version control

### Ways to Contribute

1. **🐛 Bug Reports** - Report bugs and issues
2. **✨ Feature Requests** - Suggest new features
3. **📖 Documentation** - Improve docs and guides
4. **🔧 Code Contributions** - Fix bugs or add features
5. **🧪 Testing** - Help test new features and releases
6. **🎨 UI/UX** - Improve user experience and interface

## 💻 Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/KunalG932/PostBot.git
   cd PostBot
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start MongoDB**
   ```bash
   # Local MongoDB
   mongod
   
   # Or use Docker
   docker run -d -p 27017:27017 mongo:latest
   ```

6. **Run the Bot**
   ```bash
   python main.py
   ```

## 🔄 Making Changes

### Branch Naming Convention

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions/updates

### Development Workflow

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow coding standards
   - Add tests if applicable
   - Update documentation

3. **Test your changes**
   ```bash
   # Run tests
   python -m pytest tests/
   
   # Test the bot locally
   python main.py
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add description of your changes"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] Self-review of the code has been performed
- [ ] Tests have been added/updated as needed
- [ ] Documentation has been updated
- [ ] No merge conflicts with main branch

### PR Template

```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing
- [ ] Tested locally
- [ ] Added/updated tests
- [ ] All tests pass

## Screenshots (if applicable)
Add screenshots for UI changes.

## Additional Notes
Any additional information about the changes.
```

### Review Process

1. **Automatic Checks** - All CI checks must pass
2. **Code Review** - At least one maintainer review required
3. **Testing** - Ensure all tests pass
4. **Documentation** - Check if docs need updates
5. **Merge** - Squash and merge approved PRs

## 📏 Coding Standards

### Python Style Guide

- Follow **PEP 8** style guidelines
- Use **type hints** where applicable
- Write **docstrings** for functions and classes
- Use **meaningful variable names**
- Keep functions **small and focused**

### Code Structure

```python
"""
Module docstring explaining the purpose
"""
from typing import Optional, List
import asyncio

from aiogram import types
from aiogram.filters import Command

# Constants at the top
EXAMPLE_CONSTANT = "value"

class ExampleClass:
    """Class docstring"""
    
    def __init__(self, param: str):
        self.param = param
    
    async def example_method(self, data: Optional[dict] = None) -> bool:
        """Method docstring
        
        Args:
            data: Optional dictionary parameter
            
        Returns:
            Boolean success status
        """
        # Implementation
        return True

@router.message(Command("example"))
async def example_handler(message: types.Message):
    """Handler docstring"""
    try:
        # Handler logic
        await message.reply("Success!")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")
```

### Database Conventions

- Use **descriptive collection names**
- Add **indexes** for frequently queried fields
- Use **proper error handling** for database operations
- Follow **MongoDB best practices**

## 🧪 Testing

### Test Structure

```
tests/
├── unit/
│   ├── test_handlers.py
│   ├── test_utils.py
│   └── test_database.py
├── integration/
│   └── test_bot_flow.py
└── conftest.py
```

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, Mock

from handlers.start import cmd_start

@pytest.mark.asyncio
async def test_start_command():
    """Test start command handler"""
    # Mock message
    message = Mock()
    message.from_user.id = 12345
    message.reply = AsyncMock()
    
    # Call handler
    await cmd_start(message)
    
    # Assert
    message.reply.assert_called_once()
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest tests/unit/test_handlers.py

# Run with verbose output
python -m pytest -v
```

## 📚 Documentation

### Documentation Standards

- Use **clear and concise language**
- Include **code examples** where helpful
- Add **screenshots** for UI features
- Keep **README.md** up to date
- Document **API changes** in CHANGELOG.md

### API Documentation

```python
async def send_post(
    channel_id: int,
    content: str,
    media: Optional[List[str]] = None,
    buttons: Optional[List[dict]] = None
) -> bool:
    """Send a post to a Telegram channel.
    
    Args:
        channel_id: The Telegram channel ID
        content: The text content of the post
        media: Optional list of media file paths
        buttons: Optional list of inline keyboard buttons
        
    Returns:
        True if post was sent successfully, False otherwise
        
    Raises:
        ValueError: If channel_id is invalid
        TelegramError: If Telegram API returns an error
        
    Example:
        >>> await send_post(
        ...     channel_id=-1001234567890,
        ...     content="Hello World!",
        ...     buttons=[{"text": "Click me", "url": "https://example.com"}]
        ... )
        True
    """
```

## 🎯 Feature Development Guidelines

### New Feature Checklist

- [ ] **Research** - Is this feature needed?
- [ ] **Design** - How should it work?
- [ ] **Implementation** - Write the code
- [ ] **Testing** - Add comprehensive tests
- [ ] **Documentation** - Update docs and README
- [ ] **Review** - Get feedback from maintainers

### Database Schema Changes

1. **Plan the migration** carefully
2. **Backup existing data** before changes
3. **Write migration scripts** if needed
4. **Test with sample data** thoroughly
5. **Document the changes** in CHANGELOG.md

## 🐛 Bug Reports

### Before Reporting

1. **Search existing issues** to avoid duplicates
2. **Test with latest version** to ensure bug still exists
3. **Gather all relevant information** about the issue

### Bug Report Template

```markdown
**Bug Description**
A clear description of what the bug is.

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Screenshots**
If applicable, add screenshots.

**Environment**
- OS: [e.g., Windows 10, Ubuntu 20.04]
- Python version: [e.g., 3.9.0]
- Bot version: [e.g., 1.0.0]

**Additional Context**
Any other context about the problem.
```

## 📞 Getting Help

### Communication Channels

- **GitHub Issues** - Bug reports and feature requests
- **Telegram Channel** - [@incognitobots](https://t.me/incognitobots)
- **Developer Contact** - [@DevIncognito](https://t.me/DevIncognito)

### Questions and Support

1. **Check the documentation** first
2. **Search existing issues** for similar questions
3. **Ask in the community** before creating new issues
4. **Provide context** when asking for help

## 🏆 Recognition

Contributors will be recognized in:

- **README.md** contributors section
- **CHANGELOG.md** for significant contributions
- **GitHub contributors** page
- **Special thanks** in release notes

## 📄 License

By contributing to PostBot, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

**Thank you for contributing to PostBot! 🚀**

For questions about contributing, contact [@DevIncognito](https://t.me/DevIncognito) or join our community at [@incognitobots](https://t.me/incognitobots).
