from __future__ import annotations


class ResponseStyle:
    @staticmethod
    def focusing(target: str) -> str:
        return f"Focusing {target}."

    @staticmethod
    def switched_window(direction: str) -> str:
        if direction == "previous":
            return "Switching to the previous window."
        return "Switching to the next window."

    @staticmethod
    def clipboard_copied() -> str:
        return "Copied."

    @staticmethod
    def clipboard_pasted() -> str:
        return "Pasted."

    @staticmethod
    def clipboard_empty() -> str:
        return "The clipboard is empty."

    @staticmethod
    def clipboard_saved_note() -> str:
        return "Saved the clipboard to your notes."

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
