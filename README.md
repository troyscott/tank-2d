# tank

A 2D side-view turn-based artillery duel in Python + pygame. One human vs. one AI, best-of-five, destructible terrain, per-round wind, three difficulty levels. 

Featuring a vibrant cyberpunk visual overhaul with procedural particle systems, screen shake, and glowing neon artillery. The game ships silent — all feedback is visual; see `specs/SPEC.md` § 7 for the rationale.

![screenshot](docs/screenshot.png)

## Run

```sh
micromamba create -p ./.venv -c conda-forge -y python=3.13 pygame numpy pytest
.venv/bin/python main.py
```

(Plain `python -m venv` + `pip install -r requirements.txt` works too.)

## Controls

| key | action |
|---|---|
| ← / → | aim angle |
| ↑ / ↓ | power |
| Space | fire |
| 1 / 2 / 3 | menu — Easy / Medium / Hard |
| R | next round (after a round) / back to menu (after a match) |
| ESC | quit |

## Tests

```sh
.venv/bin/pytest tests/ -q
```

## Browser build (itch.io / GitHub Pages)

The game can be compiled to WebAssembly with [pygbag](https://pypi.org/project/pygbag/) so it runs in a browser tab.

```sh
.venv/bin/pip install pygbag
.venv/bin/python -m pygbag --build --width 1024 --height 640 --title "Tank Game" main.py
```

The static bundle lands in `build/web/` (~60 KB plus the standard pygbag runtime, fetched from CDN at first load). For a local browser test, drop `--build` and visit the URL pygbag prints. To publish on **itch.io**, zip `build/web/`, create a new project marked "HTML", and upload the zip with "This file will be played in the browser" checked.

`pygbag.ini` excludes `.venv`, `tests`, `docs`, and other dev directories from the bundle so only the source is shipped.

If the browser build misbehaves (grey/red screen, audio missing, stuck on load), see [`docs/browser-build.md`](docs/browser-build.md) for the gotchas we hit and how each one is worked around.

## Deploying to itch.io

The web bundle can be pushed to a public itch.io page via [butler](https://itch.io/docs/butler/) (itch's CLI).

**One-time setup:**

1. Create the project page on itch.io (web UI). Kind: HTML; remember the slug — it must match `fableworks/tank-2d` (or set `ITCH_PROJECT`).
2. Install butler. **Note**: `brew install butler` installs an unrelated Mac app (`Butler.app`) — itch.io's butler isn't on Homebrew under that name. Download the binary directly from itch's CDN:
   ```sh
   ARCH=$(uname -m); [ "$ARCH" = "arm64" ] && CH=darwin-arm64 || CH=darwin-amd64
   mkdir -p ~/.local/bin && cd /tmp
   curl -fL -o butler.zip "https://broth.itch.zone/butler/${CH}/LATEST/archive/default"
   unzip -o butler.zip && chmod +x butler && mv butler ~/.local/bin/
   grep -q '.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   exec zsh && butler -V
   ```
   On Linux, swap `darwin-arm64` / `darwin-amd64` for `linux-amd64`.
3. Get an API key from <https://itch.io/user/settings/api-keys> and export it in your shell:
   ```sh
   echo 'export BUTLER_API_KEY=your-key-here' >> ~/.zshrc && source ~/.zshrc
   ```

**Local one-liner:**

```sh
scripts/deploy-itch.sh v0.1.1
```

Builds the bundle and pushes to `troyscott/tank-2d:html5` with the given userversion label. Override `ITCH_PROJECT`, `ITCH_CHANNEL`, or `PYTHON` via env if needed.

**Auto-deploy on GitHub release:**

`.github/workflows/deploy-itch.yml` triggers when you publish a GitHub release (or via the Actions tab → "Run workflow"). It needs the API key as a repo secret:

- GitHub → Settings → Secrets and variables → Actions → New repository secret → name `BUTLER_API_KEY`, value = your itch API key.

After that, `gh release create v0.1.1 --target main --title "..." --notes "..."` will produce a build on itch.io within ~30 seconds.

51 tests cover terrain generation + craters, projectile physics, damage falloff, AI solver convergence, match-flow logic, and audio synthesis.

## Design

See [`specs/SPEC.md`](specs/SPEC.md) for the full design and the slice-by-slice build roadmap. The architecture diagram is in [`specs/tank_artillery_architecture_v2.svg`](specs/tank_artillery_architecture_v2.svg).

## License

MIT — see [LICENSE](LICENSE).
