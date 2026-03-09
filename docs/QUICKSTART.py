"""
Quick Start Guide for Urban Pulse Backend Development
Run this guide step by step to get the system running locally.
"""

import sys
import subprocess
import time
from pathlib import Path
import shutil


def print_header(title: str):
    """Print section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_step(number: int, description: str):
    """Print step"""
    print(f"\n[STEP {number}] {description}")


def run_command(command: str, description: str = None) -> bool:
    """Run a shell command"""
    if description:
        print(f"  Running: {description}")
    print(f"  $ {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ✗ Error: {result.stderr}")
            return False
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"  ✗ Exception: {str(e)}")
        return False


def check_file_exists(filepath: str) -> bool:
    """Check if file exists"""
    exists = Path(filepath).exists()
    print(f"  {'✓' if exists else '✗'} {filepath}: {'Found' if exists else 'Not found'}")
    return exists


def main():
    """Run setup guide"""
    print_header("URBAN PULSE BACKEND - QUICK START GUIDE")
    
    print("\n📋 PRE-REQUISITES")
    print("  This guide assumes you have:")
    print("  • Python 3.11+")
    print("  • MongoDB running locally or via Docker")
    print("  • Git (for version control)")
    
    # Step 1: Check environment
    print_step(1, "Verify environment and files")
    
    essential_files = [
        "requirements.txt",
        "app.py",
        "models.py",
        "database.py",
        "data_processor.py",
        "config.py",
        "zillow_properties_listing.csv",
    ]
    
    print("\n  Checking essential files:")
    missing_files = []
    for filepath in essential_files:
        if not check_file_exists(filepath):
            missing_files.append(filepath)
    
    if missing_files:
        print(f"\n  ✗ Missing files: {missing_files}")
        print("  Please ensure all files are in the project directory")
        return False
    
    print("\n  ✓ All essential files found")
    
    # Step 2: Install dependencies
    print_step(2, "Install Python dependencies")
    
    print("\n  Installing packages from requirements.txt...")
    if not run_command("pip install -r requirements.txt", "pip install"):
        print("\n  ✗ Failed to install dependencies")
        return False
    
    print("\n  ✓ Dependencies installed")
    
    # Step 3: Start MongoDB
    print_step(3, "Start MongoDB")
    
    print("\n  MongoDB is required. Choose one option:")
    print("\n  Option A: Docker (Recommended)")
    print("    $ docker run -d -p 27017:27017 --name urban_pulse_mongo mongo:latest")
    print("\n  Option B: Local installation")
    print("    macOS: brew services start mongodb-community")
    print("    Windows: mongod (if installed)")
    print("    Linux: sudo systemctl start mongod")
    print("\n  Please ensure MongoDB is running, then press Enter...")
    input()
    
    # Verify MongoDB connection
    print("\n  Verifying MongoDB connection...")
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        print("  ✓ MongoDB connected successfully")
    except Exception as e:
        print(f"  ✗ Cannot connect to MongoDB: {str(e)}")
        print("  Please ensure MongoDB is running on localhost:27017")
        return False
    
    # Step 4: Load data
    print_step(4, "Load Zillow data into MongoDB")
    
    print("\n  Running data processing pipeline...")
    print("  This may take a few minutes for large datasets...")
    
    if not run_command("python setup.py", "python setup.py"):
        print("\n  ✗ Data loading failed")
        print("  Troubleshooting:")
        print("  • Check that zillow_properties_listing.csv exists")
        print("  • Verify MongoDB is running")
        print("  • Review error messages above")
        return False
    
    print("\n  ✓ Data loaded successfully")
    
    # Step 5: Start API
    print_step(5, "Start the FastAPI application")
    
    print("\n  Starting API server...")
    print("  The server will start in a new terminal.")
    print("  Once started, you can access:")
    print("    • API: http://localhost:8000")
    print("    • Swagger Docs: http://localhost:8000/docs")
    print("    • ReDoc: http://localhost:8000/redoc")
    print("\n  Command to run:")
    print("    $ uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    
    # Step 6: Test API
    print_step(6, "Test API endpoints (in another terminal)")
    
    print("\n  Once the API is running, test it with:")
    print("    1. Quick health check:")
    print("       $ curl http://localhost:8000/health")
    print("\n    2. Get all boroughs:")
    print("       $ curl http://localhost:8000/api/boroughs")
    print("\n    3. Get top growth zones:")
    print("       $ curl http://localhost:8000/api/top-growth-zones")
    print("\n    4. Run example script:")
    print("       $ python api_examples.py")
    
    # Step 7: Next steps
    print_header("✓ QUICK START COMPLETE!")
    
    print("\n📚 NEXT STEPS")
    print("\n  1. Review Documentation:")
    print("     • README_BACKEND.md - Full documentation")
    print("     • API endpoint details: http://localhost:8000/docs")
    print("\n  2. Explore Endpoints:")
    print("     • GET /api/boroughs - All borough metrics")
    print("     • GET /api/top-growth-zones - Top opportunities")
    print("     • GET /api/properties/search - Advanced search")
    print("\n  3. Load Your Own Data:")
    print("     • Replace zillow_properties_listing.csv with your data")
    print("     • POST /api/admin/load-data?clear_existing=true")
    print("\n  4. Customize Configuration:")
    print("     • Edit .env file to change settings")
    print("     • Adjust feature weights in config.py")
    print("     • Modify data processor logic in data_processor.py")
    print("\n  5. Deploy to Production:")
    print("     • See DEPLOYMENT section in README_BACKEND.md")
    print("     • Docker deployment with docker-compose")
    print("     • Cloud platforms (AWS, GCP, Heroku)")
    
    print("\n💡 USEFUL COMMANDS")
    print("\n  # View database stats")
    print("  $ python cli.py show-stats")
    print("\n  # Show top boroughs")
    print("  $ python cli.py show-boroughs")
    print("\n  # Test API")
    print("  $ python cli.py test-api")
    print("\n  # View configuration")
    print("  $ python cli.py config-show")
    
    print("\n🐳 DOCKER ALTERNATIVE")
    print("\n  For Docker-based setup:")
    print("  $ docker-compose up -d")
    print("\n  Then load data:")
    print("  $ curl -X POST http://localhost:8000/api/admin/load-data")
    
    print("\n📖 DOCUMENTATION")
    print("  • API Docs: http://localhost:8000/docs")
    print("  • README: README_BACKEND.md")
    print("  • Examples: api_examples.py")
    print("  • Configuration: config.py")
    
    print("\n" + "="*70)
    print("Happy coding! 🚀")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
