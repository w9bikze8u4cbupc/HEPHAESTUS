#!/usr/bin/env python3
"""Check what BOARD component was extracted."""
import json
from pathlib import Path

manifest = json.load(open("test_output/tm_final_demo/MOBIUS_READY/manifest.json"))

print("BOARD tier components:")
print("="*60)
board_items = [i for i in manifest['items'] if i['size_tier'] == 'BOARD']

if board_items:
    for item in board_items:
        print(f"\nFile: {item['file_name']}")
        print(f"Page: {item['page_index']}")
        print(f"Size: {item['width']}x{item['height']} px")
        print(f"Physical: {item['bbox_width_in']:.2f}\" x {item['bbox_height_in']:.2f}\"")
        print(f"Source bbox: {item['source_bbox']}")
else:
    print("No BOARD tier components found!")

print("\n" + "="*60)
print("Checking for large components that might be the main board...")
print("="*60)

# Look for components with large area
large_items = sorted(manifest['items'], key=lambda x: x['width'] * x['height'], reverse=True)[:5]

for i, item in enumerate(large_items, 1):
    area = item['width'] * item['height']
    print(f"\n{i}. {item['file_name']}")
    print(f"   Page: {item['page_index']}, Tier: {item['size_tier']}")
    print(f"   Size: {item['width']}x{item['height']} px (area: {area:,})")
    print(f"   Physical: {item['bbox_width_in']:.2f}\" x {item['bbox_height_in']:.2f}\"")
