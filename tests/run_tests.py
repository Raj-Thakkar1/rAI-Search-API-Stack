import pytest
import sys
import os

if __name__ == "__main__":
    # Add project root to sys.path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("Running tests...")
    retcode = pytest.main(["-v", "tests"])
    sys.exit(retcode)
