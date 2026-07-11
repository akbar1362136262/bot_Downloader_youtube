import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def check_dependencies() -> bool:
    missing = []
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        missing.append("yt-dlp")
    try:
        import aiogram  # noqa: F401
    except ImportError:
        missing.append("aiogram")
    try:
        import loguru  # noqa: F401
    except ImportError:
        missing.append("loguru")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    return True


def ensure_env() -> bool:
    base = get_base_dir()
    env_path = base / ".env"

    if env_path.exists():
        with open(env_path) as f:
            content = f.read()
        if "BOT_TOKEN=" in content and "your_telegram" not in content:
            return True

    if "BOT_TOKEN" in os.environ:
        return True

    env_sample = base / ".env.example"
    if env_sample.exists():
        print("No valid .env file found!")
        print(f"Copy {env_sample.name} to .env and set your BOT_TOKEN")
    else:
        print("No .env file found. Create one with BOT_TOKEN=your_token")
        print(f"Expected location: {env_path}")
    return False


async def health_check_server():
    """Run a minimal HTTP health check server for Railway."""
    port = int(os.environ.get("PORT", 8080))
    import aiohttp.web as web

    async def health(request):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health check server running on port {port}")


async def main():
    if not check_dependencies():
        sys.exit(1)

    base = get_base_dir()
    sys.path.insert(0, str(base))

    if not ensure_env():
        print("Set BOT_TOKEN as an environment variable or create a .env file.")
        sys.exit(1)

    is_railway = "RAILWAY_SERVICE_NAME" in os.environ or "RAILWAY_PUBLIC_DOMAIN" in os.environ

    from bot.main import main as bot_main

    if is_railway:
        asyncio.create_task(health_check_server())

    try:
        await bot_main()
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
