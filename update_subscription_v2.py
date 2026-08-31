#!/usr/bin/env python3
import asyncio
import base64
import json
import os
import re
import time
from datetime import datetime

import aiohttp

from config_generator import KaringConfigGenerator
from geo_resolver import GeoResolver
from source_discoverer import SourceDiscoverer
from source_manager import SourceManager
from source_validator import SourceValidator
from speed_test import SpeedTester
from warp_key_generator import WARPKeyGenerator
from xray_protection import XrayProtection


class AutoSubscriptionBuilder:
    def __init__(self):
        self.source_manager = SourceManager()
        self.disc
