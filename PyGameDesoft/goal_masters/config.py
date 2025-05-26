import json
import os

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class ConfigManager:
    def __init__(self):
        self.settings = {}
        self.load_config()

    def load_config(self):
        """Loads configuration from the JSON file."""
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                self.settings = json.load(f)
            print(f"Configuration loaded from {CONFIG_FILE_PATH}")
        except FileNotFoundError:
            print(f"Error: Configuration file {CONFIG_FILE_PATH} not found.")
            # You might want to fall back to default values or raise an exception
            self.settings = { # Default values as a fallback
                "min_kick_strength": 15.0,
                "max_kick_strength": 35.0,
                "max_kick_curve":    3.0
            }
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {CONFIG_FILE_PATH}.")
            # Fallback or error handling
            self.settings = {
                "min_kick_strength": 15.0,
                "max_kick_strength": 35.0,
                "max_kick_curve":    3.0
            }


    def get_setting(self, key, default=None):
        """Returns a setting value."""
        return self.settings.get(key, default)

    def reload_config(self):
        """Reloads the configuration from the file."""
        print("Reloading configuration...")
        self.load_config()

# Global instance
config_manager = ConfigManager()

if __name__ == '__main__':
    # Example usage:
    print(f"Min Kick Strength: {config_manager.get_setting('min_kick_strength')}")
    print(f"Max Kick Strength: {config_manager.get_setting('max_kick_strength')}")
    print(f"Max Kick Curve: {config_manager.get_setting('max_kick_curve')}")

    # Simulate a change in config.json and reload
    # For a real test, you'd manually change config.json then run reload
    # For example, create a temporary modified config.json to test reload
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump({"min_kick_strength": 20.0, "max_kick_strength": 40.0, "max_kick_curve": 4.0}, f)
        config_manager.reload_config()
        print(f"Reloaded Min Kick Strength: {config_manager.get_setting('min_kick_strength')}")
    finally:
        # Restore original config
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump({"min_kick_strength": 15.0, "max_kick_strength": 35.0, "max_kick_curve": 3.0}, f)
        print("Original config restored.")
