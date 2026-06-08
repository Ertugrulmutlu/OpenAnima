# Contributing

Thanks for helping improve OpenAnima.

## Development Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run the app locally with `python main.py`.

## Contribution Guidelines

- Keep changes focused and easy to review.
- Avoid committing generated files, local virtual environments, build output, caches, or personal configuration.
- Wrap all user-facing UI strings in `self.tr()` (or `QCoreApplication.translate`) to support the application's localization infrastructure.
- Prefer small fixes over broad refactors unless the refactor is explicitly planned.
- Update documentation when a user-facing workflow, release process, or setup step changes.

## Before Opening a Pull Request

- Run the app locally for the workflow you changed.
- If you modified any UI strings, run `python tools/update_translations.py` to sync and compile translation files.**
- Run any relevant checks or tests available in the repository.
- Review `git status` and ensure only intentional files are included.
