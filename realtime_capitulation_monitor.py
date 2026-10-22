#!/usr/bin/env python3
"""Compatibility entry point for the legacy Capitulation monitor filename.

The production service runs ``realtime_capitulation_monitor_fixed.py``.  This
module is kept so existing deployment commands and imports do not silently use
the older, incompatible detector API.  The actual implementation lives in the
server-synchronized monitor module.
"""

import asyncio


async def main() -> None:
    """Run the active server monitor implementation."""
    from realtime_capitulation_monitor_fixed import main as active_main

    await active_main()


if __name__ == "__main__":
    print("[DEPRECATED] Using realtime_capitulation_monitor.py; production entry point is realtime_capitulation_monitor_fixed.py")
    asyncio.run(main())
