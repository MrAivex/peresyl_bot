import asyncio
import logging

import yaml

from orchestrator import Orchestrator

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

async def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    orch = Orchestrator(config)
    await orch.start()

if __name__ == "__main__":
    asyncio.run(main())