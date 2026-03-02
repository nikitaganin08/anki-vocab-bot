from __future__ import annotations

import asyncio

from app.bot.runtime import run_polling_bot


def main() -> None:
    asyncio.run(run_polling_bot())


if __name__ == "__main__":
    main()
