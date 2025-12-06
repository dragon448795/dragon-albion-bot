# absqlite.py - 兼容層
import aiosqlite
import sys

# 將 aiosqlite 重新導出為 absqlite
sys.modules['absqlite'] = aiosqlite

# 複製所有屬性
for attr in dir(aiosqlite):
    if not attr.startswith('_'):
        setattr(sys.modules[__name__], attr, getattr(aiosqlite, attr))

__version__ = "1.0.0"
__name__ = "absqlite"