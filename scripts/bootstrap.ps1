param(
    [switch]$IncludeWakeWord
)

$ErrorActionPreference = "Stop"

Write-Host "Installing desktop voice assistant in smaller dependency groups..."

python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest

$groups = @(
    "pillow pystray pyttsx3",
    "sounddevice faster-whisper ollama",
    "pyautogui"
)

foreach ($group in $groups) {
    Write-Host "Installing: $group"
    python -m pip install $group
}

if ($IncludeWakeWord) {
    Write-Host "Installing optional wake word support..."
    python -m pip install openwakeword
}

try {
    & ollama list | Out-Null
} catch {
    Write-Warning "Ollama CLI not available on PATH."
}

Write-Host "Bootstrap complete."
