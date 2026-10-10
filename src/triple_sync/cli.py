"""Command-line utilities."""
import argparse
from triple_sync.config import Settings

def main() -> int:
    parser = argparse.ArgumentParser(prog="triple-sync")
    parser.add_argument("command", choices=["check-config"])
    args = parser.parse_args()
    if args.command == "check-config":
        missing = Settings.from_env().missing_for_sync()
        if missing:
            print("Missing required environment variables:")
            print("\\n".join(f"  - {name}" for name in missing))
            return 1
        print("Required AniList and MAL configuration is present.")
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
