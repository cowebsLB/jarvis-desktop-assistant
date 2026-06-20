# Documentation Index

This folder is the project record for the desktop voice assistant.

Use it to track:

- what the assistant currently does
- how the system is structured
- which APIs and local dependencies are in use
- what bugs were found and how they were fixed
- whether a fix is temporary, partial, or intended to be permanent
- what features and integrations are planned next

## Files

- `architecture.md`: runtime structure, module responsibilities, and data flow
- `features.md`: implemented features, behavior, and current limitations
- `apis-and-dependencies.md`: local runtimes, third-party APIs, and external assets
- `issues-and-fixes.md`: bug history, root cause, resolution, and fix durability
- `roadmap.md`: planned work and future additions

## Update Rules

When new work is done later:

1. Update `features.md` if behavior changes.
2. Update `apis-and-dependencies.md` if a new API, model, or library is added.
3. Add an entry to `issues-and-fixes.md` if a bug or failure mode was investigated.
4. Move items in `roadmap.md` from planned to implemented when they ship.

Documentation updates are part of the definition of done for this project.

## Current State

The project is a Windows-first local desktop voice assistant built in Python with:

- system tray runtime
- local wake word support
- local faster-whisper speech-to-text
- local text-to-speech
- Ollama-backed local QA
- direct internal web research
- local SQLite research archive
- spoken weather support
- safe desktop actions for typing, opening apps, opening sites, and web search
- audible listen cue
- adaptive silence-based command capture
- structured JSONL request history
- personalized spoken feedback and voice styling
