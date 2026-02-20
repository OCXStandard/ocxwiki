"""Test to verify AppConfig reads and preserves custom configuration values."""

#  Copyright (c) 2026. OCX Consortium https://3docx.org. See the LICENSE

import tempfile
from pathlib import Path
from ocxwiki.commands.config import AppConfig


def test_config_preserves_custom_values():
    """Test that custom config values are preserved across save/load cycles."""

    # Create a temporary config file with custom values
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write("""[general]
app_name = My Custom App
history_file = ~/.my_custom_history
max_history = 500
log_level = DEBUG

[display]
theme = dark
show_timestamps = true

[custom_section]
custom_key = custom_value
""")
        temp_config_path = f.name

    try:
        # Load the config
        print(f"Loading config from: {temp_config_path}")
        config = AppConfig(config_path=temp_config_path)

        # Verify custom values are loaded
        print("\n✓ Testing initial load:")
        assert config.get("general", "app_name") == "My Custom App", "app_name not preserved"
        print(f"  app_name: {config.get('general', 'app_name')}")

        assert config.get("general", "history_file") == "~/.my_custom_history", "history_file not preserved"
        print(f"  history_file: {config.get('general', 'history_file')}")

        assert config.getint("general", "max_history") == 500, "max_history not preserved"
        print(f"  max_history: {config.getint('general', 'max_history')}")

        assert config.get("general", "log_level") == "DEBUG", "log_level not preserved"
        print(f"  log_level: {config.get('general', 'log_level')}")

        assert config.get("display", "theme") == "dark", "theme not preserved"
        print(f"  theme: {config.get('display', 'theme')}")

        assert config.getboolean("display", "show_timestamps") == True, "show_timestamps not preserved"
        print(f"  show_timestamps: {config.getboolean('display', 'show_timestamps')}")

        assert config.get("custom_section", "custom_key") == "custom_value", "custom_section not preserved"
        print(f"  custom_key: {config.get('custom_section', 'custom_key')}")

        # Save the config
        print("\n✓ Saving config...")
        config.save()

        # Load again to verify values are still preserved after save
        print("\n✓ Testing reload after save:")
        config2 = AppConfig(config_path=temp_config_path)

        assert config2.get("general", "app_name") == "My Custom App", "app_name lost after save"
        print(f"  app_name: {config2.get('general', 'app_name')}")

        assert config2.get("general", "log_level") == "DEBUG", "log_level lost after save"
        print(f"  log_level: {config2.get('general', 'log_level')}")

        assert config2.get("display", "theme") == "dark", "theme lost after save"
        print(f"  theme: {config2.get('display', 'theme')}")

        assert config2.get("custom_section", "custom_key") == "custom_value", "custom_section lost after save"
        print(f"  custom_key: {config2.get('custom_section', 'custom_key')}")

        print("\n✅ All tests passed! Config preserves custom values correctly.")

    finally:
        # Clean up
        Path(temp_config_path).unlink(missing_ok=True)


def test_config_applies_defaults_for_missing_keys():
    """Test that defaults are applied only for missing keys."""

    # Create a config file with only some values
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write("""[general]
app_name = Partial Config
log_level = WARNING
""")
        temp_config_path = f.name

    try:
        print("\n" + "="*60)
        print("Testing default application for missing keys")
        print("="*60)

        config = AppConfig(config_path=temp_config_path)

        # Custom value should be preserved
        assert config.get("general", "app_name") == "Partial Config"
        print(f"✓ Custom value preserved: app_name = {config.get('general', 'app_name')}")

        assert config.get("general", "log_level") == "WARNING"
        print(f"✓ Custom value preserved: log_level = {config.get('general', 'log_level')}")

        # Missing values should use defaults
        assert config.get("general", "history_file") == "~/.cli_app_history"
        print(f"✓ Default applied: history_file = {config.get('general', 'history_file')}")

        assert config.getint("general", "max_history") == 100
        print(f"✓ Default applied: max_history = {config.getint('general', 'max_history')}")

        # Missing section should use defaults
        assert config.get("display", "theme") == "default"
        print(f"✓ Default section applied: theme = {config.get('display', 'theme')}")

        print("\n✅ Default application works correctly!")

    finally:
        Path(temp_config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_config_preserves_custom_values()
    test_config_applies_defaults_for_missing_keys()
    print("\n🎉 All configuration tests passed!")
