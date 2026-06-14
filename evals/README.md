# Code Djinn Eval Fixtures

This folder contains a small deterministic target project for search and ask-mode
evaluation.

Layout:

- `target/`: dummy project with source, docs, config, data, scripts, and tests.
- `questions/`: user-facing prompts to ask Code Djinn.
- `answers/`: expected answers with file paths and evidence lines.

The fixtures avoid depending on real repository files. For date-related
questions, answers use explicit `updated:` front matter rather than filesystem
mtime, which changes on checkout.
