from __future__ import annotations


class ResponseStyle:
    @staticmethod
    def calculation(expression: str, result: str) -> str:
        return f"{expression} equals {result}."

    @staticmethod
    def opening(target: str) -> str:
        return f"At once. Opening {target}."

    @staticmethod
    def opening_site(target: str) -> str:
        return f"At once. Opening {target}."

    @staticmethod
    def opening_folder(target: str) -> str:
        return f"Opening your {target} folder."

    @staticmethod
    def opening_file(target: str) -> str:
        return f"Opening {target}."

    @staticmethod
    def file_not_found(target: str) -> str:
        return f"I couldn't find a local file matching {target}."

    @staticmethod
    def typed() -> str:
        return "Done. I've typed it."

    @staticmethod
    def web_search(query: str) -> str:
        return f"Right away. Looking up {query}."

    @staticmethod
    def archive_recall(query: str) -> str:
        return f"Reviewing what I've stored on {query}."

    @staticmethod
    def archive_empty(query: str) -> str:
        return f"I don't have anything stored on {query} yet."

    @staticmethod
    def no_speech() -> str:
        return "I didn't catch that. After the beep, one clear command should suffice."

    @staticmethod
    def stt_unavailable() -> str:
        return "Speech recognition is not ready yet. Warm the speech model, and I'll be ready."
