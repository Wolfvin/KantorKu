"""
Example 4: Configuration — Using kantorku.toml for setup.

Shows how to configure kantorku entirely from a TOML file,
including workers, providers, pool, and memory settings.

Usage:
    python examples/04_from_config.py
"""

import asyncio
from kantorku import Office


async def main():
    # Load all configuration from TOML file
    # This is the recommended way for production use
    office = Office.from_config("kantorku.toml")

    await office.initialize()

    # Check what we have
    print(f"Workers: {office.registry.all_worker_ids}")
    print(f"Pool status: {office.get_pool_status()}")
    print(f"Providers: {office.router.configured_providers}")

    # The office is fully configured — just run
    result = await office.run(
        "Build a simple rate limiter middleware in Python",
        auto_accept=True,
    )

    import json
    print(json.dumps(result, indent=2, default=str)[:2000])

    await office.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
