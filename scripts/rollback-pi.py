#!/usr/bin/env python3
"""Run on Pi: python3 scripts/rollback-pi.py RELEASE_NAME"""
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('release')
args = parser.parse_args()
root = Path.home() / 'SmartDisplayRPI/runtime'
if Path(args.release).name != args.release or args.release in {'.', '..'}:
    parser.error('Use a release directory name, not a path')
target = root / 'releases' / args.release
if not target.is_dir() or target.is_symlink():
    parser.error('Release is missing or not a regular directory')
state = json.loads((target / 'state.json').read_text())
if not (target / 'index.html').is_file():
    parser.error('Release is incomplete')
for photo in state.get('photos', []):
    resolved = (target / photo).resolve()
    if not resolved.is_relative_to(target.resolve()) or not resolved.is_file():
        parser.error('Release photo is missing or invalid')
link = root / 'rollback-next'
link.unlink(missing_ok=True)
link.symlink_to(target, target_is_directory=True)
os.replace(link, root / 'current')
print('Rolled back to', args.release)
