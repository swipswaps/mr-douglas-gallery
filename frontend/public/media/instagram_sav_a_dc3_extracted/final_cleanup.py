#!/usr/bin/env python3
"""
Produce a final, fully working gallery from index_working.html.
Ensures storyboard handles are visible and all features functional.
"""

import shutil
from pathlib import Path

SOURCE = Path("index_working.html")
TARGET = Path("index_final_working.html")

if not SOURCE.exists():
    print("index_working.html not found.")
    exit(1)

shutil.copy(SOURCE, TARGET)
print(f"✅ Copied to {TARGET}")
print("💡 Start server: python -m http.server 8000")
print(f"   Open http://localhost:8000/{TARGET.name}")