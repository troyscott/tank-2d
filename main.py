# /// script
# dependencies = ["numpy"]
# ///
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tanks.game import Game  # noqa: E402


async def main() -> None:
    await Game().run()


if __name__ == "__main__":
    asyncio.run(main())
