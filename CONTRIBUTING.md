# Contributing to EpubSage

We welcome contributions! Please follow these guidelines:

## Development Setup

1. Clone the repository.
2. Install `uv` if you haven't already.
3. Run `make install` to set up the development environment.

## Workflow

1. Create a feature branch.
2. Make your changes.
3. Ensure code quality:
   - Run `make format` to apply formatting rules.
   - Run `make lint` to check for issues.
   - Run `make test` to verify logic.
4. Submit a Pull Request.

## Coding Standards

- Follow PEP 8 (enforced by `ruff`).
- Add docstrings to new functions and classes.
- Ensure all tests pass.
