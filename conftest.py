import os
import tempfile

# Scripts resolve the private repo at import. Point them at a throwaway dir so
# tests never touch (or depend on finding) a real private repo.
os.environ["LIFEREPO_PRIVATE_ROOT"] = tempfile.mkdtemp(prefix="liferepo-private-test-")
