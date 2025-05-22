#!/usr/bin/env python3

def load_config(config_file='config.ini'):
    """
    Load configuration from config file.
    Returns a dictionary of configuration values.
    
    Required fields:
    - USERNAME: Canvas username/email
    - PASSWORD: Canvas password
    - LOGIN_URL: Full URL to the Canvas login endpoint
    - STUDENT: Student name for database tracking
    """
    config = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        # Validate required configuration
        required_fields = [
            'USERNAME',
            'PASSWORD',
            'LOGIN_URL',
            'STUDENT'
        ]
        
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
            
        return config
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file '{config_file}' not found")
    except Exception as e:
        raise Exception(f"Error loading configuration: {str(e)}") 