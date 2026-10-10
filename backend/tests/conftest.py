from pathlib import Path
import sys
import os
import tempfile

# Unit tests never contact live sources; startup loading is enabled explicitly in its test.
os.environ["KESSLER_AUTO_REFRESH_CATALOG"] = "false"
os.environ["KESSLER_DATA_DIR"] = tempfile.mkdtemp(prefix="kessler-tests-")

sys.path.insert(0, str(Path(__file__).parents[1]))
