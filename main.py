#!/usr/bin/env python3
import asyncio
import sys

from update_subscription_v2 import AutoSubscriptionBuilder


async def full_pipeline():
    print("=== VPN Subscription Generator ===")
    
    builder = AutoSubscriptionBuilder()
    
    try:
        result = await builder.build()
        if result:
            print(f"\nSubscription generated successfully")
            print(f"Size: {len(result)} bytes")
            return 0
        else:
            print("\nBuild failed")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(full_pipeline())
    sys.exit(exit_code)
