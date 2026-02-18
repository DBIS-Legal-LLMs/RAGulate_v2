# Backend/api_v2/app/core/errors.py

"""
ERROR Codes for internal error handling
"""

__all__ = [
    "UNKNOWN_ERROR_0",
    "MESSAGE_10000_",
    "CHAT_100_NOT_FOUND",
    "FOLDER_1000_NOT_FOUND",
    "FOLDER_1001_NAME_EXISTS",
    "FOLDER_1002_MAX_DEPTH_EXCEEDED",
    "",
]

"""
BASIC
"""
UNKNOWN_ERROR_0 = 0


"""
CHAT / MESSAGE ERRORS
"""
MESSAGE_10000_ = 10000

CHAT_100_NOT_FOUND = 100


"""
FOLDER ERRORS
"""
FOLDER_1000_NOT_FOUND = 1000
FOLDER_1001_NAME_EXISTS = 1001
FOLDER_1002_MAX_DEPTH_EXCEEDED = 1002


def __dir__() -> list[str]:
    return sorted(list(__all__))