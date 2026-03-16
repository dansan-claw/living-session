#!/usr/bin/env python3
"""
Living Session - Configuration System

Robust configuration management with validation and defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class LivingSessionConfig:
    """Configuration for a living session."""
    
    # Required
    project_name: str
    trello_board_id: str
    
    # Trello credentials (can be from env)
    trello_api_key: Optional[str] = None
    trello_token: Optional[str] = None
    
    # Timing (seconds)
    interval: int = 3600
    min_interval: int = 60
    max_interval: int = 14400
    
    # Behavior
    auto_start: bool = False
    retry_attempts: int = 3
    retry_delay: int = 60
    
    # Features
    enable_chaining: bool = False
    notify_on_blocked: bool = True
    log_level: str = "INFO"
    
    # Derived
    config_path: Optional[Path] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
        
    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []
        
        # Required fields
        if not self.project_name:
            errors.append("project_name is required")
        if not self.trello_board_id:
            errors.append("trello_board_id is required")
            
        # Timing validation
        if self.interval < self.min_interval:
            errors.append(f"interval ({self.interval}) must be >= min_interval ({self.min_interval})")
        if self.interval > self.max_interval:
            errors.append(f"interval ({self.interval}) must be <= max_interval ({self.max_interval})")
        if self.min_interval >= self.max_interval:
            errors.append(f"min_interval ({self.min_interval}) must be < max_interval ({self.max_interval})")
            
        # Trello credentials
        if not self.get_trello_api_key():
            errors.append("Trello API key not found (set in config or TRELLO_API_KEY env)")
        if not self.get_trello_token():
            errors.append("Trello token not found (set in config or TRELLO_TOKEN env)")
            
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
            
        return True
        
    def get_trello_api_key(self) -> Optional[str]:
        """Get Trello API key from config or environment."""
        return self.trello_api_key or os.environ.get('TRELLO_API_KEY')
        
    def get_trello_token(self) -> Optional[str]:
        """Get Trello token from config or environment."""
        return self.trello_token or os.environ.get('TRELLO_TOKEN')
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'project_name': self.project_name,
            'trello_board_id': self.trello_board_id,
            'trello_api_key': self.trello_api_key,
            'trello_token': self.trello_token,
            'interval': self.interval,
            'min_interval': self.min_interval,
            'max_interval': self.max_interval,
            'auto_start': self.auto_start,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'enable_chaining': self.enable_chaining,
            'notify_on_blocked': self.notify_on_blocked,
            'log_level': self.log_level
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LivingSessionConfig':
        """Create config from dictionary."""
        # Filter to only valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


class ConfigManager:
    """Manages loading and saving of living session configurations."""
    
    def __init__(self):
        self.config_path = Path.home() / ".openclaw" / "config.yaml"
        self._config_cache: Optional[Dict[str, Any]] = None
        
    def _load_raw_config(self) -> Dict[str, Any]:
        """Load raw config from file."""
        if not self.config_path.exists():
            return {}
            
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"⚠️  Error parsing config file: {e}")
            return {}
        except Exception as e:
            print(f"⚠️  Error loading config: {e}")
            return {}
            
    def get_global_config(self) -> Dict[str, Any]:
        """Get global living_sessions config."""
        raw = self._load_raw_config()
        return raw.get('living_sessions', {})
        
    def get_project_config(self, project_name: str) -> Optional[LivingSessionConfig]:
        """
        Get configuration for a specific project.
        
        Loads from ~/.openclaw/config.yaml
        """
        global_config = self.get_global_config()
        
        # Get project-specific config
        project_data = global_config.get(project_name)
        if not project_data:
            return None
            
        # Merge with defaults
        defaults = {
            'project_name': project_name,
            'interval': global_config.get('default_interval', 3600),
            'max_interval': global_config.get('max_interval', 14400),
            'retry_attempts': global_config.get('retry_attempts', 3)
        }
        
        # Project config overrides defaults
        merged = {**defaults, **project_data}
        merged['config_path'] = self.config_path
        
        try:
            return LivingSessionConfig.from_dict(merged)
        except ValueError as e:
            print(f"❌ Invalid configuration for project '{project_name}':\n{e}")
            return None
            
    def list_projects(self) -> List[str]:
        """List all configured projects."""
        global_config = self.get_global_config()
        
        # Filter out non-project keys (like 'default_interval')
        reserved_keys = {'default_interval', 'max_interval', 'retry_attempts'}
        projects = [k for k in global_config.keys() if k not in reserved_keys]
        
        return projects
        
    def create_project_config(self, project_name: str, trello_board_id: str,
                             **kwargs) -> bool:
        """
        Create a new project configuration.
        
        Saves to ~/.openclaw/config.yaml
        """
        try:
            # Load existing config
            raw_config = self._load_raw_config()
            
            if 'living_sessions' not in raw_config:
                raw_config['living_sessions'] = {}
                
            # Create project config
            project_config = {
                'trello_board_id': trello_board_id,
                **kwargs
            }
            
            # Add to config
            raw_config['living_sessions'][project_name] = project_config
            
            # Save back
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)
                
            print(f"✅ Created configuration for '{project_name}'")
            print(f"   Saved to: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create config: {e}")
            return False
            
    def update_project_config(self, project_name: str, **updates) -> bool:
        """Update an existing project configuration."""
        try:
            raw_config = self._load_raw_config()
            
            if 'living_sessions' not in raw_config or project_name not in raw_config['living_sessions']:
                print(f"❌ Project '{project_name}' not found in config")
                return False
                
            # Update
            raw_config['living_sessions'][project_name].update(updates)
            
            # Save
            with open(self.config_path, 'w') as f:
                yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)
                
            print(f"✅ Updated configuration for '{project_name}'")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update config: {e}")
            return False
            
    def remove_project_config(self, project_name: str) -> bool:
        """Remove a project configuration."""
        try:
            raw_config = self._load_raw_config()
            
            if 'living_sessions' in raw_config and project_name in raw_config['living_sessions']:
                del raw_config['living_sessions'][project_name]
                
                with open(self.config_path, 'w') as f:
                    yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)
                    
                print(f"✅ Removed configuration for '{project_name}'")
                return True
            else:
                print(f"⚠️  Project '{project_name}' not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to remove config: {e}")
            return False
            
    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all project configurations."""
        results = {}
        
        for project_name in self.list_projects():
            config = self.get_project_config(project_name)
            if config is None:
                results[project_name] = ["Failed to load or validate"]
            else:
                results[project_name] = []
                
        return results


# CLI for config management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Living Session Config Manager")
    subparsers = parser.add_subparsers(dest='command')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new project config')
    create_parser.add_argument('project', help='Project name')
    create_parser.add_argument('board_id', help='Trello board ID')
    create_parser.add_argument('--interval', type=int, default=3600)
    create_parser.add_argument('--auto-start', action='store_true')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all projects')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show project config')
    show_parser.add_argument('project', help='Project name')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate all configs')
    
    args = parser.parse_args()
    
    manager = ConfigManager()
    
    if args.command == 'create':
        manager.create_project_config(
            args.project,
            args.board_id,
            interval=args.interval,
            auto_start=args.auto_start
        )
        
    elif args.command == 'list':
        projects = manager.list_projects()
        print(f"\n📋 Configured Projects:")
        for project in projects:
            print(f"  - {project}")
            
    elif args.command == 'show':
        config = manager.get_project_config(args.project)
        if config:
            print(f"\n📊 Configuration for '{args.project}':")
            for key, value in config.to_dict().items():
                # Mask sensitive values
                if 'token' in key.lower() or 'key' in key.lower():
                    value = '***' if value else None
                print(f"  {key}: {value}")
        else:
            print(f"❌ Project '{args.project}' not found")
            
    elif args.command == 'validate':
        results = manager.validate_all()
        print(f"\n✅ Validation Results:")
        for project, errors in results.items():
            status = "✅" if not errors else "❌"
            print(f"{status} {project}")
            for error in errors:
                print(f"   - {error}")
    else:
        parser.print_help()
