# Contributing

Thanks for contributing to Jarvis Desktop Assistant.

This project is still early, Windows-first, and intentionally conservative about voice-triggered system behavior. Changes should improve capability without weakening safety or making the runtime harder to reason about.

## Ground Rules

- Keep the assistant local-first where practical.
- Preserve explicit safety boundaries for voice actions.
- Prefer clear, testable behavior over vague smartness.
- Update the docs when shipped behavior changes.
- Do not add destructive voice actions casually.

## Development Setup

1. Install dependencies:

```powershell
pip install -e .[dev]
```

2. Optional wake word dependencies:

```powershell
pip install -e .[wakeword]
```

3. Pull the local Ollama model:

```powershell
ollama pull qwen2.5-coder:1.5B
```

4. Run the test suite:

```powershell
python -m pytest
```

## What Good Changes Look Like

- New behavior is routed intentionally, not by accidental regex overlap.
- Desktop actions fail safely and speak clearly when they cannot proceed.
- Tests cover the new route or execution path.
- Docs under `docs/` reflect the current state after the change lands.

## Expected Update Areas

If you change behavior, usually update at least one of:

- `docs/features.md`
- `docs/issues-and-fixes.md`
- `docs/apis-and-dependencies.md`
- `TODO.md`
- `README.md`

## Pull Request Notes

Before opening a PR:

- run `python -m pytest`
- keep commits focused
- describe user-facing behavior changes clearly
- call out any safety tradeoffs
- mention any manual testing you performed

## Areas That Need Help

- clipboard helpers
- focus and window targeting
- richer multi-step desktop workflows
- better ambiguity handling
- stronger local retrieval and research ranking
- future settings UI / HUD work
