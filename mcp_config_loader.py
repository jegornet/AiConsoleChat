import json
import os
from typing import Dict, Any


class McpConfigLoader:
    """Handles loading and validation of configuration files"""
    
    @staticmethod
    def load_mcp_config(config_path: str = "mcp.json") -> Dict[str, Any]:
        """Load MCP configuration from JSON file
        
        Args:
            config_path: Path to the MCP configuration file
            
        Returns:
            Dictionary containing the configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
            ValueError: If no servers are configured
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"MCP configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        servers = config.get("servers", {})
        if not servers:
            raise ValueError("No servers configured in mcp.json")
        
        return config
    
    @staticmethod
    def get_first_server_config(config: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Get the first server configuration
        
        Args:
            config: MCP configuration dictionary
            
        Returns:
            Tuple of (server_name, server_config)
        """
        servers = config.get("servers", {})
        server_name = next(iter(servers))
        server_config = servers[server_name]
        return server_name, server_config