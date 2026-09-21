"""Run HTTP contracts, including isolated sessions and read-only deployment."""
import subprocess
import sys
for pattern in ['test_api.py','test_public_demo.py']:
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-v'],check=True)
