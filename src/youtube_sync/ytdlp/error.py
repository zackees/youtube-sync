# Global flag to track keyboard interrupts
_KEYBOARD_INTERRUPT_HAPPENED = False


# Function to check and set the interrupt flag
def set_keyboard_interrupt():
    """Set the global keyboard interrupt flag."""
    global _KEYBOARD_INTERRUPT_HAPPENED
    _KEYBOARD_INTERRUPT_HAPPENED = True


def check_keyboard_interrupt():
    """Check if a keyboard interrupt has happened.

    Returns:
        bool: True if a keyboard interrupt has happened
    """
    return _KEYBOARD_INTERRUPT_HAPPENED


class KeyboardInterruptException(Exception):
    """Exception raised when a keyboard interrupt is detected."""

    pass
