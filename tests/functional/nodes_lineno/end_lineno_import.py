# Import, ImportFrom.
import a.b  # position: 2:0-2:10
import a as x  # position: 3:0-3:13
from . import x  # position: 4:0-4:15
from .a import y as y  # position: 5:0-5:21
