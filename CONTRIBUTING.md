# Contributing to Aegis

Thank you for contributing to the Aegis quantitative trading platform.

## Development Setup

```bash
# Full platform
python scripts/install-platform.py

# Exchange (C++)
cmake -B build -DCMAKE_BUILD_TYPE=Debug -DAEGIS_BUILD_TESTS=ON
cmake --build build -j
cd build && ctest --output-on-failure

# All Python tests
pytest execution/tests options/tests market-maker/tests analytics/tests aegis-quant/tests -v
```

## Pull Request Process

1. Fork and create a feature branch from `main`
2. Ensure all tests pass (45+ Python, C++ unit/integration)
3. Format C++ with `clang-format`, Python with `ruff check`
4. Add tests for new functionality
5. Update documentation and screenshots if UI changes
6. Submit PR using the template

## Code Standards

- **C++20** — Google style, no extensions, no TODOs in production code
- **Python 3.11+** — Type hints, ruff formatting, meaningful test coverage
- **TypeScript/React** — Consistent with existing dashboard patterns
- **Commits** — [Conventional Commits](https://www.conventionalcommits.org/)

## Commit Message Format

```
feat(exchange): add stop-limit order validation
feat(quant): add walk-forward hyperparameter search
feat(options): implement barrier option pricing
docs(readme): update deployment instructions
test(api): add execution simulator integration tests
build(docker): add portal service to compose
```

## Module Ownership

| Module | Path |
|--------|------|
| Exchange | `core/`, `matching-engine/`, `orderbook/`, etc. |
| Quant | `aegis-quant/` |
| Execution | `execution/` |
| Options | `options/` |
| Market Maker | `market-maker/` |
| Analytics | `analytics/` |
| Portal | `portal/` |

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
