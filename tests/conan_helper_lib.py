import os
import sys
from pathlib import Path

conan_helper_module = Path(os.path.abspath(__file__)).parent.parent.joinpath("lib")
sys.path.append(str(conan_helper_module))
