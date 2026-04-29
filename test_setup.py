#!/usr/bin/env python3
"""
Test Setup - Verify all components are ready
"""
import sys
import os

def test_imports():
    """Test if all required packages can be imported."""
    print("Testing imports...")
    errors = []

    packages = [
        ("flask", "Flask"),
        ("flask_cors", "Flask-CORS"),
        ("flask_socketio", "Flask-SocketIO"),
        ("anthropic", "Anthropic"),
        ("dotenv", "python-dotenv"),
        ("deepgram", "Deepgram SDK"),
        ("google.cloud.texttospeech", "Google Cloud TTS"),
        ("elevenlabs", "ElevenLabs"),
        ("pydub", "pydub"),
        ("soundfile", "soundfile"),
    ]

    for module, name in packages:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} - NOT INSTALLED")
            errors.append(name)

    return len(errors) == 0

def test_env_file():
    """Check if .env file exists."""
    print("\nChecking .env file...")
    if os.path.exists('.env'):
        print("  ✓ .env file exists")

        # Check for API keys
        from dotenv import load_dotenv
        load_dotenv()

        keys = {
            "ANTHROPIC_API_KEY": "REQUIRED",
            "DEEPGRAM_API_KEY": "optional",
            "ELEVENLABS_API_KEY": "optional",
            "GOOGLE_SHEETS_TRAINING_LOG_ID": "optional",
            "SLACK_WEBHOOK_URL": "optional"
        }

        missing_required = []
        for key, status in keys.items():
            value = os.getenv(key)
            if value:
                print(f"  ✓ {key} - configured")
            else:
                if status == "REQUIRED":
                    print(f"  ✗ {key} - REQUIRED but missing")
                    missing_required.append(key)
                else:
                    print(f"  ⚠ {key} - optional, not set")

        return len(missing_required) == 0
    else:
        print("  ✗ .env file NOT FOUND")
        return False

def test_directories():
    """Check if required directories exist."""
    print("\nChecking directories...")
    dirs = [
        'directives',
        'execution',
        'web/templates',
        'web/static/css',
        'web/static/js',
        '.tmp'
    ]

    all_exist = True
    for d in dirs:
        if os.path.exists(d):
            print(f"  ✓ {d}")
        else:
            print(f"  ✗ {d} - NOT FOUND")
            all_exist = False

    return all_exist

def test_files():
    """Check if required files exist."""
    print("\nChecking critical files...")
    files = [
        'execution/web_voice_server.py',
        'execution/conversation_manager.py',
        'execution/score_response.py',
        'web/templates/index.html',
        'web/static/css/style.css',
        'web/static/js/app.js',
        'directives/objection_library.md',
        'directives/voice_training_session.md',
        'directives/score_performance.md'
    ]

    all_exist = True
    for f in files:
        if os.path.exists(f):
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} - NOT FOUND")
            all_exist = False

    return all_exist

def main():
    print("=" * 60)
    print("VOICE TRAINING PLATFORM - SETUP VERIFICATION")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "Environment": test_env_file(),
        "Directories": test_directories(),
        "Files": test_files()
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All tests passed! You're ready to start the server.")
        print("\nNext steps:")
        print("  1. Add ANTHROPIC_API_KEY to .env file")
        print("  2. cd execution")
        print("  3. python3 web_voice_server.py")
        print("  4. Open http://localhost:5000")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
