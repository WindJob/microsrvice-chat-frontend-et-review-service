#!/usr/bin/env python
"""
Install and run review-service
"""
import subprocess
import sys
import os

def run_command(cmd, description=""):
    """Run a shell command"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True, cwd=os.getcwd())
    if result.returncode != 0:
        print(f"\n❌ Error executing: {description}")
        return False
    print(f"\n✅ Success: {description}")
    return True


def main():
    print("🚀 Review Service Setup & Launch")
    print("=" * 60)
    
    # Step 1: Install dependencies
    if not run_command(
        f"{sys.executable} -m pip install --upgrade pip",
        "Upgrading pip"
    ):
        sys.exit(1)
    
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing dependencies"
    ):
        sys.exit(1)
    
    # Step 2: Create .env if missing
    if not os.path.exists(".env"):
        print("\n⚙️  Creating .env file from example...")
        with open(".env.example", "r") as src:
            with open(".env", "w") as dst:
                dst.write(src.read())
        print("✅ .env file created")
    
    # Step 3: Run tests
    print("\n📋 Running tests...")
    if os.path.exists("tests/test_main.py"):
        run_command(
            f"{sys.executable} -m pytest tests/ -v",
            "Running pytest tests"
        )
    
    # Step 4: Start service
    print("\n🎯 Starting service on http://localhost:8006...")
    run_command(
        f"{sys.executable} main.py",
        "Starting review-service"
    )


if __name__ == "__main__":
    main()
