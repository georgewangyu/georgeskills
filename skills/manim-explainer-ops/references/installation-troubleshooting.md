# Installation Troubleshooting

Use the official Manim Community installation guide first. Keep each project
inside an isolated environment.

## macOS Cairo Linker Check

Manim requires Cairo and Pango. Confirm that the package metadata is visible:

```bash
pkg-config --modversion cairo
pkg-config --modversion pango
```

If `uv run python -c "import cairo"` fails with an unresolved Cairo symbol,
rebuild Pycairo while explicitly linking the Cairo library discovered by
`pkg-config`:

```bash
LDFLAGS="$(pkg-config --libs-only-L cairo) -lcairo" \
  uv sync --no-cache --reinstall-package pycairo
uv run python -c "import cairo; print(cairo.version)"
```

Do not hardcode a Homebrew prefix into the reusable project. `pkg-config`
keeps the repair portable across Apple Silicon, Intel macOS, and other package
manager prefixes. Record the workaround in the project handoff when it was
needed.

## LaTeX Check

A text-only scene can render without proving that equations will work. Before
building a `MathTex`-heavy asset, render one tiny equation scene. If LaTeX is
missing, install it according to the official Manim Community guide or choose
a truthful non-LaTeX treatment; do not convert equations to arbitrary plain
text and claim equivalent mathematical layout.
