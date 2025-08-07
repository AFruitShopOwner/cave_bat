## Cave Bat (Pygame)

A Flappy Bird–style game: fly a bat through a cave of stalactites and stalagmites. 16:9 window, keyboard/mouse controls. The bat is animated and flaps on input.

### Art Direction
- Cohesive moody paper-cut silhouette style, inspired by layered cardstock.
- Cool, desaturated palette for rock and cave layers; soft vertical gradient background.
- Layered parallax cave ridges (three depths) for a sense of scale.
- Stalactites/stalagmites are precomputed jagged meshes with inner/outer layers and subtle highlight edges.
- Bat features a rim light outline and wing membranes; flaps on input with idle flutter.
- Subtle dust motes and a vignette overlay add atmosphere.

### Controls
- Space / Left Click: flap
- R: restart
- Esc: quit

### Setup
Using a virtual environment is recommended.

Windows PowerShell example:

```powershell
cd C:\Users\Thinkbook G2 ITL\Programming\Projects\cave_bat
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
# Install package with development extras (tests, linters, type checker)
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

### Run

```powershell
# Option 1: run the package entrypoint
.\.venv\Scripts\python.exe -m cave_bat

# Option 2: installed console script
cave-bat

# Option 3: thin script delegating to the package
.\.venv\Scripts\python.exe .\main.py
```

### Tests

```powershell
.\.venv\Scripts\pytest.exe -q

# Lint, format, type-check
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\black.exe --check .
.\.venv\Scripts\mypy.exe .
```

### Development

Pre-commit hooks are configured. Install them with:

```powershell
\.venv\Scripts\pre-commit.exe install
```

### License

MIT License. See `LICENSE`.
