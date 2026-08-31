#!/usr/bin/env python3
import asyncio
import json
import os
import sys

from update_subscription_v2 import AutoSubscriptionBuilder


async def full_pipeline():
    print("=== VPN Subscription Generator ===")
    print("Starting full pipeline...")
    
    builder = AutoSubscriptionBuilder()
    await builder.init()
    
    try:
        result = await builder.build()
        print(f"\nSubscription generated successfully")
        print(f"Size: {len(result)} bytes")
        
        # Print stats
        from source_manager import SourceManager
        manager = SourceManager()
        stats = manager.get_stats()
        print(f"\nSource stats:")
        print(f"  Total: {stats['total']}")
        print(f"  Active: {stats['active']}")
        print(f"  Stale: {stats['stale']}")
        print(f"  Dead: {stats['dead']}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await builder.close()
        
    return result


if __name__ == '__main__':
    asyncio.run(full_pipeline())
