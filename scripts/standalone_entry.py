"""PyInstaller entrypoint; absolute package import works in the frozen executable."""

from claude_codex_bridge.__main__ import main

if __name__ == "__main__":
    main()
