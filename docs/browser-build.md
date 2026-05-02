# Browser build notes

The game runs in a browser tab via [pygbag](https://pypi.org/project/pygbag/) (pygame compiled to WebAssembly via Pyodide). Getting it there required navigating several browser-specific gotchas that aren't obvious from a clean native run. Captured here so future-you doesn't burn a day rediscovering them.

## Building

```sh
.venv/bin/pip install pygbag
.venv/bin/python -m pygbag --build --width 1024 --height 640 --title "Tank Game" main.py
# bundle in build/web/  (~60 KB; pygame + Python runtime are pulled from the pygbag CDN at first load)
```

For a local dev test, drop `--build` and visit the URL pygbag prints (default `http://localhost:8000`).

## Gotchas (and the fix each one)

### 1. `pygame.init()` blocks indefinitely
`pygame.init()` calls `pygame.mixer.init()` internally. In the browser, `Mix_OpenAudioDevice` waits for the AudioContext, which is gated on a user gesture and can hang Python before our app ever paints a frame.

**Fix:** initialize subsystems explicitly — `pygame.display.init()` and `pygame.font.init()` only — and never call `pygame.init()`. This applies in both `Game.__init__` and any pre-Game bootstrap code (e.g. a splash screen in `main.py`).

### 2. `pygame.font.SysFont(None, size)` hangs
`SysFont` triggers a system-font discovery pass that doesn't behave the same in WebAssembly and silently hangs.

**Fix:** use `pygame.font.Font(None, size)`, which loads pygame's bundled default font directly. Works identically on native and in the browser.

### 3. `pygame.mixer.init()` and `Sound` creation block until first user gesture
Even when called on its own, mixer init blocks on the locked AudioContext. The first user keypress / click unlocks it.

**Fix:** in `AudioSystem.__init__` we synthesize the audio buffers (numpy only — no mixer) but do **not** initialize the mixer or build `pygame.mixer.Sound` objects. Both are deferred to the first `play()` call, which only happens after a user gesture by definition (firing a shot, navigating the menu, etc.). `play()` retries `_try_init` each call until it succeeds.

### 4. `import numpy` fails immediately at module load
pygbag/pyodide installs wheels asynchronously after the page loads. If our code does `import numpy as np` at module top, it can run before pyodide finishes installing numpy and we hit `ModuleNotFoundError`.

**Fix (two-pronged):**
- Declare numpy via PEP 723 inline metadata at the top of `main.py`:
  ```python
  # /// script
  # dependencies = ["numpy"]
  # ///
  ```
- Lazy-import numpy *inside* the synth functions rather than at module top — see `src/tanks/audio.py`. So merely importing the audio module never requires numpy; only running a synth does.

### 4b. PEP 723 isn't enough — numpy install completes *after* main.py starts running
This was the sneakier follow-up to #4. Even with the dependency declared and `import numpy` deferred to inside synth functions, the installation can finish *slightly after* `main.py` begins executing. Concretely: pygbag fetches the numpy wheel during page load, but the `micropip.install()` call to actually unpack and register it is async; on a fast machine, Python execution races ahead. AudioSystem's lazy `_np()` call then hits `ModuleNotFoundError` and (without a try/except) the screen stays grey forever. Locally with numpy in the venv it works fine; only the browser exposes it.

**Symptoms:** game works locally, "stops working" when deployed to itch even though earlier deploys with the same code worked. The difference is usually that the working deploy had an incidental delay (e.g. on-canvas debug paint + sleep) that gave numpy time to install.

**Fix:** poll `import numpy` for ~3 seconds at the top of `main()` before importing anything that touches it. On native this is a single instant import; on browser it provides a deterministic wait. See `main.py:_wait_for_numpy`.

```python
async def _wait_for_numpy(max_attempts=30, delay=0.1):
    for _ in range(max_attempts):
        try:
            import numpy  # noqa: F401
            return
        except ModuleNotFoundError:
            await asyncio.sleep(delay)
```

**Always pair with a try/except in `main()`** that paints uncaught exceptions onto the canvas. Without it, *any* future timing or import error becomes a silent grey screen, since browsers don't surface Python stdout (see #7).

### 5. pygbag bundles `.venv` (and any other dot-dirs) into the apk by default
Without an explicit ignore list pygbag walks the project root and pulls in everything, producing a 200+ MB apk that contains your virtualenv. The default ignore patterns in pygbag's filter (`/.git`, `/build`, `/venv`, …) all start with a leading slash because the walk yields paths prefixed with `/`. Patterns *without* a leading slash silently don't match.

**Fix:** `pygbag.ini` at the repo root, with the leading-slash convention:
```ini
[DEPENDENCIES]
ignoreDirs = ["/.venv", "/tests", "/docs", "/specs", "/__pycache__", "/.pytest_cache", "/build", "/dist", "/.github", "/.claude"]
ignoreFiles = []
```

### 6. Async game loop is required
pygbag enters the browser's animation-frame loop and needs Python to yield to the event loop each frame. A native `while running: ...` loop will starve the browser.

**Fix:** make `Game.run()` an `async def`, end each iteration with `await asyncio.sleep(0)`, and start the program from `main.py` with `asyncio.run(main())`. Native execution under `asyncio.run` is a no-op overhead; pygbag patches `asyncio.run` to drive the browser loop.

### 7. Python `print()` doesn't go to the browser DevTools console
Python stdout is routed to pygbag's embedded vtx terminal on the page itself, not the browser's DevTools console. When debugging, prints can appear to vanish.

**Workarounds:**
- Find pygbag's terminal overlay on the page (toggleable; look for a console panel or try the `?-i` URL parameter).
- Or — what we ended up doing during bring-up — paint diagnostic status directly onto the canvas via `font.render` + `display.flip()`. The canvas itself becomes the log. Wrap the entire `main()` body in `try/except` and render the traceback on a red-tinted screen so any silent exception becomes visible.

### 8. Display pixel ratio warnings
Windows 110% display scaling produces `devicePixelRatio = 1.1`, which pygbag flags as "unsupported" in `window_canvas_adjust`. In our case it was a red herring — not the cause of any actual hang — but worth knowing about if a build looks blurry or sized oddly.

**Workaround if it does cause issues:** force `window.devicePixelRatio = 1` via a small shim in pygbag's generated `index.html`, or set Windows display scale to 100%.

## Deploying to itch.io

1. Build with `--build` (above).
2. `cd build/web && zip -r ../tank-web.zip . && cd ../..`
3. itch.io → New project → Kind: HTML → upload `tank-web.zip` → check "This file will be played in the browser".
4. Set the embedded viewport to 1024×640 to match the game canvas.

The bundle contains `index.html`, `tank-2d.apk`, `tank-2d.tar.gz`, `favicon.png`. itch.io serves them as a static page; everything else (Python, pygame, numpy) is loaded on demand from the pygbag CDN.
