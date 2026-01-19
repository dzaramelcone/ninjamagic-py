import ninjamagic.bus as bus
import ninjamagic.nightclock as nightclock
import ninjamagic.scheduler as scheduler


def test_restcheck_scheduled_at_6am(monkeypatch):
    calls = []

    def fake_cue(sig, time=None, recur=None):
        calls.append((sig, time))

    monkeypatch.setattr(scheduler, "cue", fake_cue)

    scheduler.start()

    rest_calls = [c for c in calls if isinstance(c[0], bus.RestCheck)]
    assert rest_calls
    assert rest_calls[0][1] == nightclock.NightTime(hour=6)
