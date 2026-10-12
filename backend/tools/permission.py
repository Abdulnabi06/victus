from typing import Callable, Optional

class PermissionManager:
    """
    Manages permissions for dangerous actions.
    Follows the confirm_callback pattern established in Module 1.
    """
    def __init__(self):
        self._confirm_callback: Optional[Callable[[str, str], bool]] = None

    def set_confirm_callback(self, callback: Callable[[str, str], bool]) -> None:
        """
        Set a callback that takes (action_name, details) and returns True if confirmed.
        """
        self._confirm_callback = callback

    def check_permission(self, action_name: str, details: str) -> bool:
        """
        Check if an action is permitted. If no callback is set, it defaults to False (deny).
        """
        if not self._confirm_callback:
            return False
        return self._confirm_callback(action_name, details)

# Global permission manager instance
permission_manager = PermissionManager()
