"""Group 6: multiscale PatchCore experiments."""
import os
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
os.environ.setdefault('TORCH_HOME', str(_root / '.cache/torch'))
os.environ.setdefault('MPLCONFIGDIR', str(_root / '.cache/matplotlib'))
