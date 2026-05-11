"""
Secure Schwabdev integration for mb_tools.

This package uses mb_tools.secure_config to load Schwabdev credentials
and the Schwabdev token database encryption key from an encrypted .ecfg file.
"""

# from .config import (
#     REQUIRED_ECFG_KEYS,
#     SecureSchwabConfig,
#     SecureSchwabConfigError,
#     config_from_dict,
#     load_secure_schwab_config,
#     validate_secure_schwab_dict,
# )


from .config import (
    REQUIRED_ECFG_KEYS,
    SecureSchwabConfig,
    SecureSchwabConfigError,
    config_from_dict,
    load_secure_schwab_config,
    validate_schwabdev_key_shape,
    validate_secure_schwab_dict,
)


from .client import (
    SchwabdevNotInstalledError,
    console_auth_callback,
    make_client_from_config,
    make_secure_schwab_client,
)

# __all__ = [
#     "REQUIRED_ECFG_KEYS",
#     "SecureSchwabConfig",
#     "SecureSchwabConfigError",
#     "config_from_dict",
#     "load_secure_schwab_config",
#     "validate_secure_schwab_dict",
#     "SchwabdevNotInstalledError",
#     "console_auth_callback",
#     "make_client_from_config",
#     "make_secure_schwab_client",
# ]


__all__ = [
    "REQUIRED_ECFG_KEYS",
    "SecureSchwabConfig",
    "SecureSchwabConfigError",
    "config_from_dict",
    "load_secure_schwab_config",
    "validate_schwabdev_key_shape",
    "validate_secure_schwab_dict",
    "SchwabdevNotInstalledError",
    "console_auth_callback",
    "make_client_from_config",
    "make_secure_schwab_client",
]