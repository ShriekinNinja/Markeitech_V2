from markeitech.runtime.actor import BoundedEventIdentityWindow


def test_identity_window_suppresses_duplicates_and_bounds_memory() -> None:
    identities = BoundedEventIdentityWindow(2)

    assert identities.observe("event-1")
    assert identities.observe("event-2")
    assert not identities.observe("event-1")
    assert identities.duplicate_count == 1

    assert identities.observe("event-3")
    assert identities.observe("event-2")
    assert identities.duplicate_count == 1
