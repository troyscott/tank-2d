# Tank Game - Developer Guide

See [specs/SPEC.md](specs/SPEC.md) for the complete design and architecture.

## Setup
```sh
micromamba create -p ./.venv -c conda-forge -y python=3.13 pygame numpy pytest
# or
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Game
```sh
./.venv/bin/python main.py
```

## Running Tests
```sh
./.venv/bin/pytest tests/ -q
```

## Linting & Type Checking
To prevent silent failures, the project uses `ruff` (linter) and `mypy` (type checker).
```sh
./.venv/bin/ruff check src/tanks main.py tests
./.venv/bin/mypy src/tanks main.py
```

## Building for the Web
The game can be compiled to WebAssembly using `pygbag` to run in the browser.
```sh
./.venv/bin/pip install pygbag
./.venv/bin/python -m pygbag --build --width 1024 --height 640 --title "Tank Game" main.py
```
*Note: Ensure all assets are loaded dynamically so they are packaged properly by pygbag.*

## Audio Architecture
The game uses a **Hybrid Cross-Platform Audio Architecture**:
- `afplay`: Used natively on macOS (zero-latency CoreAudio).
- `winsound`: Used natively on Windows (asynchronous C-bindings).
- `pygame.mixer`: Used in WebAssembly builds or as a fallback.
If testing natively on macOS, ensure you aren't using an AirPlay/Bluetooth device to experience the true zero-latency audio sync.