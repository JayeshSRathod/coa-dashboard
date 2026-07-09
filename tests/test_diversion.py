import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.diversion import detect_diversion


def test_no_diversion_on_first_poll():
    assert detect_diversion(None, 24400) is None
    print("first poll (no prior strike) -> no diversion OK")


def test_no_diversion_when_wall_unchanged():
    assert detect_diversion(24400, 24400) is None
    print("unchanged wall -> no diversion OK")


def test_diversion_on_upward_migration():
    # Resistance wall migrated up from 24400 to 24450 (writers rolled up)
    result = detect_diversion(24400, 24450)
    assert result == 24425.0
    print("upward migration diversion OK:", result)


def test_diversion_on_downward_migration():
    # Support wall migrated down from 24400 to 24350
    result = detect_diversion(24400, 24350)
    assert result == 24375.0
    print("downward migration diversion OK:", result)


if __name__ == "__main__":
    test_no_diversion_on_first_poll()
    test_no_diversion_when_wall_unchanged()
    test_diversion_on_upward_migration()
    test_diversion_on_downward_migration()
    print("All diversion tests passed.")
