from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileMatch:
    path: Path
    score: float


class DesktopControl:
    _SKIP_DIR_NAMES = {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
    }

    def folder_aliases(self) -> dict[str, Path]:
        home = Path.home()
        return {
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "document": home / "Documents",
            "downloads": home / "Downloads",
            "download": home / "Downloads",
            "music": home / "Music",
            "pictures": home / "Pictures",
            "photos": home / "Pictures",
            "videos": home / "Videos",
            "home": home,
            "user folder": home,
        }

    def resolve_folder(self, target: str) -> Path | None:
        normalized = self._normalize_name(target)
        aliases = self.folder_aliases()
        if normalized in aliases:
            return aliases[normalized]
        if normalized.endswith(" folder") and normalized[: -len(" folder")] in aliases:
            return aliases[normalized[: -len(" folder")]]
        return None

    def search_file(self, query: str, *, limit: int = 1) -> list[FileMatch]:
        normalized_query = self._normalize_name(query)
        candidates: list[FileMatch] = []
        seen: set[Path] = set()

        for root in self._search_roots():
            if not root.exists():
                continue
            for path in self._walk_files(root):
                if path in seen:
                    continue
                score = self._score_file_match(normalized_query, path)
                if score <= 0:
                    continue
                candidates.append(FileMatch(path=path, score=score))
                seen.add(path)

        candidates.sort(key=lambda item: (-item.score, len(item.path.name), str(item.path).lower()))
        return candidates[:limit]

    @classmethod
    def _normalize_name(cls, value: str) -> str:
        lowered = value.lower().strip()
        for phrase in ("folder", "file", "please", "for me", "right now"):
            lowered = lowered.replace(phrase, " ")
        lowered = lowered.replace("-", " ")
        return " ".join(lowered.split())

    @staticmethod
    def _score_file_match(query: str, path: Path) -> float:
        filename = path.name.lower()
        stem = path.stem.lower()
        query_compact = query.replace(" ", "")
        stem_compact = stem.replace(" ", "")
        name_compact = filename.replace(" ", "")

        if filename == query or stem == query:
            return 1.0
        if filename.startswith(query) or stem.startswith(query):
            return 0.95
        if query in filename or query in stem:
            return 0.88
        if query_compact == stem_compact or query_compact == name_compact:
            return 0.84

        similarity = max(
            difflib.SequenceMatcher(None, query, stem).ratio(),
            difflib.SequenceMatcher(None, query, filename).ratio(),
            difflib.SequenceMatcher(None, query_compact, stem_compact).ratio(),
        )
        return similarity if similarity >= 0.72 else 0.0

    def _search_roots(self) -> list[Path]:
        roots = [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
        ]
        cwd = Path.cwd()
        if cwd not in roots:
            roots.append(cwd)
        unique: list[Path] = []
        for root in roots:
            if root not in unique:
                unique.append(root)
        return unique

    @classmethod
    def _walk_files(cls, root: Path):
        for current_root, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in cls._SKIP_DIR_NAMES and not dirname.startswith(".")
            ]
            for filename in filenames:
                if filename.startswith("."):
                    continue
                yield Path(current_root) / filename
