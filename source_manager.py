#!/usr/bin/env python3
import json
import os
from datetime import datetime, timedelta


SOURCES_FILE = "sources.json"
SOURCES_BACKUP = "sources.json.bak"
MIN_SOURCES = 100
MAX_SOURCES = 150


class SourceManager:
    def __init__(self):
        self.sources = []
        self.load()
        
    def load(self):
        if os.path.exists(SOURCES_FILE):
            with open(SOURCES_FILE) as f:
                self.sources = json.load(f)
                
    def save(self):
        if os.path.exists(SOURCES_FILE):
            os.replace(SOURCES_FILE, SOURCES_BACKUP)
            
        with open(SOURCES_FILE, "w") as f:
            json.dump(self.sources, f, indent=2)
            
    def add_sources(self, new_sources):
        existing_urls = {s["url"] for s in self.sources}
        added = 0
        
        for src in new_sources:
            if src["url"] not in existing_urls:
                src["added"] = datetime.utcnow().isoformat()
                src["fail_count"] = 0
                src["last_success"] = None
                self.sources.append(src)
                added += 1
                
        return added
        
    def remove_dead(self, dead_urls):
        before = len(self.sources)
        self.sources = [s for s in self.sources if s["url"] not in dead_urls]
        return before - len(self.sources)
        
    def mark_stale(self, stale_urls):
        for s in self.sources:
            if s["url"] in stale_urls:
                s["stale"] = True
                s["stale_since"] = datetime.utcnow().isoformat()
                
    def update_stats(self, url, success, node_count=0):
        for s in self.sources:
            if s["url"] == url:
                if success:
                    s["fail_count"] = 0
                    s["last_success"] = datetime.utcnow().isoformat()
                    s["last_node_count"] = node_count
                    s["stale"] = False
                else:
                    s["fail_count"] = s.get("fail_count", 0) + 1
                    
    def get_active_sources(self, max_fail=3):
        active = []
        for s in self.sources:
            fails = s.get("fail_count", 0)
            stale = s.get("stale", False)
            if fails < max_fail and not stale:
                active.append(s)
        return active
        
    def get_source_urls(self):
        return [s["url"] for s in self.get_active_sources()]
        
    def needs_discovery(self):
        active = len(self.get_active_sources())
        return active < MIN_SOURCES
        
    def get_stats(self):
        total = len(self.sources)
        active = len(self.get_active_sources())
        stale = len([s for s in self.sources if s.get("stale")])
        dead = total - active - stale
        
        return {
            "total": total,
            "active": active,
            "stale": stale,
            "dead": dead,
            "need_discovery": active < MIN_SOURCES
        }
        
    def rebuild_from_validation(self, validation_report):
        alive_urls = {a["url"] for a in validation_report.get("alive", [])}
        dead_urls = {d["url"] for d in validation_report.get("dead", [])}
        stale_urls = {s["url"] for s in validation_report.get("stale", [])}
        
        removed = self.remove_dead(dead_urls)
        self.mark_stale(stale_urls)
        
        for a in validation_report.get("alive", []):
            self.update_stats(a["url"], True, a.get("nodes_found", 0))
            
        for d in validation_report.get("dead", []):
            self.update_stats(d["url"], False)
            
        self.save()
        return removed
        
    def export_for_fetcher(self):
        active = self.get_active_sources()
        return [s["url"] for s in active[:MAX_SOURCES]]


def main():
    manager = SourceManager()
    
    try:
        with open("live_sources.json") as f:
            live = json.load(f)
        added = manager.add_sources(live)
        print(f"Added {added} new sources")
    except:
        print("No live_sources.json")
        
    stats = manager.get_stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")
    
    manager.save()


if __name__ == '__main__':
    main()
