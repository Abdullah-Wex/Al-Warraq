# Contributing to EpubSage

Thanks for your interest in contributing!

## Reporting bugs and requesting features

Open a GitHub Issue. Please include:
- For bugs: a minimal reproduction (sample EPUB if relevant), the command or code that triggered it, and the actual vs expected behavior.
- For features: the use case you're trying to solve, not just the proposed API.

## Development setup

```bash
git clone https://github.com/Abdullah-Wex/epubsage.git
cd epubsage
uv sync
uv run pytest
```

## Workflow

1. Create a feature branch: `feat/<short-slug>` or `fix/<short-slug>`.
2. Make your changes. Keep commits focused — small, reviewable diffs are easier to merge.
3. Run quality gates before pushing:
   ```bash
   uv run ruff check epubsage/ tests/
   uv run mypy epubsage/
   uv run pytest tests/ -v
   ```
4. Open a Pull Request against `main`.

## Coding standards

- Follow the existing module structure (flat `epubsage/` package, no nested subpackages).
- Add type hints to public functions.
- Add tests for new behavior — both happy path and edge cases.
- For parsing changes, include a malformed-input test.

## Commit messages

Use Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
