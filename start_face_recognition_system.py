#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Face Recognition System Startup Script
"""

import os
import sys
import subprocess
import webbrowser
import time

def start_system():
    """Start the face recognition system"""
    print("🚀 STARTING FACE RECOGNITION SYSTEM")
    print("=" * 50)
    
    # Check if virtual environment is activated
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment is active")
    else:
        print("⚠️  Virtual environment not detected")
        print("   Please activate venv first: venv\\Scripts\\activate")
    
    print("\n📋 System Information:")
    print(f"   • Python: {sys.version.split()[0]}")
    print(f"   • Working directory: {os.getcwd()}")
    
    # Check if manage.py exists
    if not os.path.exists('manage.py'):
        print("❌ manage.py not found. Please run from project root directory.")
        return False
    
    print("\n🔧 Starting Django development server...")
    print("   URL: http://127.0.0.1:8000")
    print("   Press Ctrl+C to stop the server")
    print("\n" + "=" * 50)
    
    try:
        # Start Django server
        subprocess.run([sys.executable, 'manage.py', 'runserver'], check=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting server: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def show_usage_instructions():
    """Show usage instructions"""
    print("\n📖 HOW TO USE FACE RECOGNITION:")
    print("=" * 50)
    print("1. 🌐 Open browser and go to: http://127.0.0.1:8000")
    print("2. 🔐 Login as lecturer")
    print("3. 📅 Go to 'Attendance' section")
    print("4. 🏫 Select a classroom")
    print("5. 📹 Click 'Attendance by Face'")
    print("6. ✅ Allow camera permissions when prompted")
    print("7. 👤 Face recognition will start automatically")
    print("\n🎯 LECTURER LOGIN CREDENTIALS:")
    print("   Check with admin for lecturer username/password")
    print("\n💡 TIPS:")
    print("   • Ensure good lighting for face recognition")
    print("   • Look directly at camera")
    print("   • Wait for green box and progress bar")
    print("   • System needs 3 consecutive frames to confirm identity")

if __name__ == '__main__':
    print("🎭 FACE RECOGNITION ATTENDANCE SYSTEM")
    print("=" * 50)
    
    show_usage_instructions()
    
    print("\n" + "=" * 50)
    input("Press Enter to start Django server...")
    
    success = start_system()
    
    if success:
        print("\n✅ System shutdown successfully")
    else:
        print("\n❌ System encountered errors")
    
    input("\nPress Enter to exit...")