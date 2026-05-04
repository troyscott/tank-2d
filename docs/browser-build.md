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

**Fix:** initialize subsystems explicitly — `pygame.display.init()` and `pygame.font.init()` only — and never call `pygame.init()`. This applies in both `Renderer.__init__` and any pre-Game bootstrap code (e.g. a splash screen in `main.py`).

### 2. `pygame.font.SysFont(None, size)` hangs
`SysFont` triggers a system-font discovery pass that doesn't behave the same in WebAssembly and silently hangs.

**Fix:** use `pygame.font.Font(None, size)`, which loads pygame's bundled default font directly. Works identically on native and in the browser.

### 3. `pygame.mixer.init()` and `Sound` creation block until first user gesture
Even when called on its own, mixer init blocks on the locked AudioContext. The first user keypress / click unlocks it.

**Fix:** in `AudioSystem.__init__` we don't initialize the mixer or build `pygame.mixer.Sound` objects — those are deferred to the first `play()` call, which only happens after a user gesture by definition (firing a shot, navigating the menu, etc.). `play()` retries `_try_init` each call until it succeeds.

### 3b. Pygame doesn't resample — `mixer.init(rate=...)` is a request, not a guarantee
On macOS native and many other platforms, `pygame.mixer.init(22050, -16, 2, ...)` silently comes up at the system's native rate (44100). If you synthesize at 22050 and the mixer plays at 44100, sounds play at 2× speed an octave higher *and* SDL's interpolation introduces sub-sample timing jitter between any layered components — which fragments single `play()` calls into multiple perceived events. Symptoms include "tank hits sound like 2-3 events even though we only called `play('hit')` once" — which we mis-diagnosed as a synth-design issue for several iterations before checking the actual rate.

**Fix:** synthesize at `pygame.mixer.get_init()[0]` (the actual rate the mixer came up at), not at the rate you requested. See `_synth_*(sr)` in `src/tanks/audio.py` and `AudioSystem._try_init` for the pattern: pass the actual rate into the synth functions and only build the buffers + Sound objects after init succeeds.

### 4. pygbag bundles `.venv` (and any other dot-dirs) into the apk by default
Without an explicit ignore list pygbag walks the project root and pulls in everything, producing a 200+ MB apk that contains your virtualenv. The default ignore patterns in pygbag's filter (`/.git`, `/build`, `/venv`, …) all start with a leading slash because the walk yields paths prefixed with `/`. Patterns *without* a leading slash silently don't match.

**Fix:** `pygbag.ini` at the repo root, with the leading-slash convention:
```ini
[DEPENDENCIES]
ignoreDirs = ["/.venv", "/tests", "/docs", "/specs", "/__pycache__", "/.pytest_cache", "/build", "/dist", "/.github", "/.claude"]
ignoreFiles = []
```

### 5. Async game loop is required
pygbag enters the browser's animation-frame loop and needs Python to yield to the event loop each frame. A native `while running: ...` loop will starve the browser.

**Fix:** make the `while True:` loop in `main.py` yield each frame with `await asyncio.sleep(0)`, and start the program with `asyncio.run(main())`. Native execution under `asyncio.run` is a no-op overhead; pygbag patches `asyncio.run` to drive the browser loop.

### 6. Python `print()` doesn't go to the browser DevTools console
Python stdout is routed to pygbag's embedded vtx terminal on the page itself, not the browser's DevTools console. When debugging, prints can appear to vanish.

**Workarounds:**
- Find pygbag's terminal overlay on the page (toggleable; look for a console panel or try the `?-i` URL parameter).
- Or — what we ended up doing during bring-up — paint diagnostic status directly onto the canvas via `font.render` + `display.flip()`. The canvas itself becomes the log. Wrap the entire `main()` body in `try/except` and render the traceback on a red-tinted screen so any silent exception becomes visible.

### 7. Display pixel ratio warnings
Windows 110% display scaling produces `devicePixelRatio = 1.1`, which pygbag flags as "unsupported" in `window_canvas_adjust`. In our case it was a red herring — not the cause of any actual hang — but worth knowing about if a build looks blurry or sized oddly.

**Workaround if it does cause issues:** force `window.devicePixelRatio = 1` via a small shim in pygbag's generated `index.html`, or set Windows display scale to 100%.

## Deploying to itch.io

1. Build with `--build` (above).
2. `cd build/web && zip -r ../tank-web.zip . && cd ../..`
3. itch.io → New project → Kind: HTML → upload `tank-web.zip` → check "This file will be played in the browser".
4. Set the embedded viewport to 1024×640 to match the game canvas.

The bundle contains `index.html`, `tank-2d.apk`, `tank-2d.tar.gz`, `favicon.png`. itch.io serves them as a static page; everything else (Python, pygame, numpy) is loaded on demand from the pygbag CDN.
