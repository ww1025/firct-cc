import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))  # uniform-assigner/
sys.path.insert(0, _here)                    # tests/
