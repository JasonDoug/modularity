# Contributing to Modularity

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/modularity.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `make test`
6. Commit: `git commit -am "Add your feature"`
7. Push: `git push origin feature/your-feature`
8. Create a Pull Request

## Development Setup

```bash
# Install dependencies
make install

# Setup dev environment
make dev-setup

# Run tests
make test
```

## Code Standards

- Python: Follow PEP 8
- JavaScript: Follow ESLint rules
- Write tests for new features
- Update documentation

## Commit Messages

Format: `type(scope): message`

Types: feat, fix, docs, test, refactor, chore

Example: `feat(sdk): add capability validation`

## Testing

All PRs must pass tests:

```bash
make test
make lint
```

## Questions?

Open an issue or join our discussions!
