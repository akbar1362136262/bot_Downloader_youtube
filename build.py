import os
import shutil
import subprocess
import sys
from pathlib import Path


def clean_build():
    for p in ["build", "dist"]:
        path = Path(p)
        if path.exists():
            shutil.rmtree(path, ignore_errors=False)
    for p in Path(".").rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    print("Cleaned build artifacts.")


def ensure_icon() -> Path:
    icon_path = Path("bot_icon.ico")
    if not icon_path.exists():
        print("Generating icon...")
        subprocess.run([sys.executable, "generate_icon.py"], check=True)
    return icon_path


def build_exe():
    icon_path = ensure_icon()

    print("Building executable with PyInstaller...")
    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "DownloaderBot",
        "--icon", str(icon_path.resolve()),
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", "build",
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic_settings",
        "--hidden-import", "yt_dlp",
        "--hidden-import", "aiogram",
        "--hidden-import", "loguru",
        "--hidden-import", "aiofiles",
        "--hidden-import", "browser_cookie3",
        "--hidden-import", "dotenv",
        "--collect-all", "yt_dlp",
        "--collect-all", "aiogram",
        "run.py",
    ]
    subprocess.run(cmd, check=True)

    exe_path = Path("dist") / "DownloaderBot.exe"
    if exe_path.exists():
        print(f"\nBuild successful!")
        print(f"Executable: {exe_path.resolve()}")
        print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
        print("\nRun it directly or create a shortcut!")
    else:
        print("\nBuild failed - executable not found.")
        sys.exit(1)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"

    if mode == "clean":
        clean_build()
    elif mode == "build":
        build_exe()
    elif mode == "rebuild":
        clean_build()
        build_exe()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python build.py [clean|build|rebuild]")
        sys.exit(1)


if __name__ == "__main__":
    main()
