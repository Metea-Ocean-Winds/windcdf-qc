import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

class PanelSettingsManager:
    """Manages saving and loading of panel appearance settings."""
    
    def __init__(self, settings_file: str = "current_view_settings.yaml"):
        self.settings_file = Path(settings_file)
    
    def save_panel_settings(self, panels_config: List[Dict[str, Any]], variable_colors: Dict[str, str]) -> None:
        """
        Save panel settings to YAML file.
        
        Args:
            panels_config: List of panel configurations
                Each dict should have:
                - panel_index: int
                - name: str (panel name)
                - y_axis_locked: bool
                - y_min: float (optional)
                - y_max: float (optional)
            variable_colors: Dict mapping (source, z, variable) to color
                Format: "source|z|variable": "#hexcolor"
        """
        settings = {
            'version': '0.1.1',
            'panels': panels_config,
            'variable_colors': variable_colors
        }
        
        with open(self.settings_file, 'w') as f:
            yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
    
    def load_panel_settings(self) -> Optional[Dict[str, Any]]:
        """
        Load panel settings from YAML file.
        
        Returns:
            Dictionary with 'panels' and 'variable_colors' keys, or None if file doesn't exist
        """
        if not self.settings_file.exists():
            return None
        
        with open(self.settings_file, 'r') as f:
            settings = yaml.safe_load(f)
        
        return {
            'panels': settings.get('panels', []),
            'variable_colors': settings.get('variable_colors', {})
        }
    
    def settings_exist(self) -> bool:
        """Check if settings file exists."""
        return self.settings_file.exists()