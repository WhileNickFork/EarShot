#!/usr/bin/env python3
"""
GNSS utilities with D-Bus fallback support for Particle Tachyon.
"""

import subprocess
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class GNSSQueryError(Exception):
    """Custom exception for GNSS query failures."""
    pass


def query_gnss_ril_ctl() -> Dict[str, Any]:
    """
    Query GNSS using particle-tachyon-ril-ctl command.
    
    Returns:
        Dictionary of GNSS data
        
    Raises:
        GNSSQueryError: If query fails
    """
    try:
        result = subprocess.run(
            ['particle-tachyon-ril-ctl', 'gnss'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise GNSSQueryError(f"Command failed: {result.stderr}")
        
        # Parse output
        gnss_data = {}
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Convert numeric values
                try:
                    if '.' in value:
                        gnss_data[key] = float(value)
                    elif value.isdigit():
                        gnss_data[key] = int(value)
                    else:
                        gnss_data[key] = value
                except ValueError:
                    gnss_data[key] = value
        
        return gnss_data
        
    except subprocess.TimeoutExpired:
        raise GNSSQueryError("Command timed out")
    except FileNotFoundError:
        raise GNSSQueryError("particle-tachyon-ril-ctl not found")
    except Exception as e:
        raise GNSSQueryError(f"Unexpected error: {e}")


def query_gnss_dbus() -> Dict[str, Any]:
    """
    Query GNSS using D-Bus interface as fallback.
    
    Returns:
        Dictionary of GNSS data
        
    Raises:
        GNSSQueryError: If query fails
    """
    try:
        # D-Bus command to get GNSS data
        cmd = [
            'dbus-send',
            '--system',
            '--print-reply',
            '--dest=io.particle.tachyon.GNSS.Modem',
            '/io/particle/tachyon/GNSS/Modem',
            'org.freedesktop.DBus.Properties.GetAll',
            'string:io.particle.tachyon.GNSS.Modem'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise GNSSQueryError(f"D-Bus command failed: {result.stderr}")
        
        # Parse D-Bus output (simplified - actual parsing would be more complex)
        # This is a placeholder - real implementation would parse D-Bus variant format
        logger.warning("D-Bus parsing not fully implemented - using ril-ctl format")
        raise GNSSQueryError("D-Bus parser not implemented")
        
    except subprocess.TimeoutExpired:
        raise GNSSQueryError("D-Bus query timed out")
    except FileNotFoundError:
        raise GNSSQueryError("dbus-send not found")
    except Exception as e:
        raise GNSSQueryError(f"D-Bus error: {e}")


def query_gnss_with_fallback() -> Optional[Dict[str, Any]]:
    """
    Query GNSS with automatic fallback to D-Bus if ril-ctl fails.
    
    Returns:
        Dictionary of GNSS data or None if all methods fail
    """
    # Try primary method
    try:
        logger.debug("Attempting GNSS query via ril-ctl")
        return query_gnss_ril_ctl()
    except GNSSQueryError as e:
        logger.warning(f"ril-ctl failed: {e}")
    
    # Try D-Bus fallback
    try:
        logger.debug("Attempting GNSS query via D-Bus")
        return query_gnss_dbus()
    except GNSSQueryError as e:
        logger.warning(f"D-Bus failed: {e}")
    
    logger.error("All GNSS query methods failed")
    return None