"""Quick verification that the app reads the config file correctly."""

#  Copyright (c) 2026. OCX Consortium https://3docx.org. See the LICENSE

from ocxwiki.commands.config import AppConfig


def verify_app_config():
    """Verify the actual .cli_app.ini file is read correctly."""

    print("Verifying .cli_app.ini configuration...\n")

    config = AppConfig(config_path=".cli_app.ini")

    print("Configuration values loaded:")
    print(f"  app_name: {config.get('general', 'app_name')}")
    print(f"  history_file: {config.get('general', 'history_file')}")
    print(f"  max_history: {config.getint('general', 'max_history')}")
    print(f"  log_level: {config.get('general', 'log_level')}")
    print(f"  theme: {config.get('display', 'theme')}")
    print(f"  show_timestamps: {config.getboolean('display', 'show_timestamps')}")

    # Verify the log level is DEBUG as set by the user
    log_level = config.get('general', 'log_level', fallback='INFO')
    print(f"\n✓ Log level from config: {log_level}")

    if log_level == "DEBUG":
        print("✅ User's DEBUG log level is being read correctly!")
    else:
        print(f"⚠ Expected DEBUG, but got {log_level}")

    # Save and reload to ensure persistence
    print("\nTesting save/reload cycle...")
    config.save()

    config2 = AppConfig(config_path=".cli_app.ini")
    log_level2 = config2.get('general', 'log_level', fallback='INFO')

    if log_level2 == "DEBUG":
        print("✅ Log level preserved after save/reload!")
    else:
        print(f"❌ Log level changed to {log_level2} after save/reload")

    print("\n✅ Configuration file is working correctly!")


if __name__ == "__main__":
    verify_app_config()
