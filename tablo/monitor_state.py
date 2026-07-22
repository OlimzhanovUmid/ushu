"""In-process monitor snapshot channel (replaces the filesystem pub/sub).

The projector page holds an SSE connection to ``monitor_stream``; publishers
(activation, score-to-monitor, tablo-to-monitor) call :func:`publish` with the
fully rendered pages. Single-process waitress means one shared instance is
enough; a lock keeps snapshot swaps atomic so a reader never sees a torn page
count/content pair.
"""
import threading


class MonitorState:
    def __init__(self):
        self._cond = threading.Condition()
        self._pages = []
        self._revision = 0

    def publish(self, pages):
        """Atomically replace the displayed pages and wake waiting streams."""
        with self._cond:
            self._pages = list(pages)
            self._revision += 1
            self._cond.notify_all()

    def snapshot(self):
        with self._cond:
            return self._revision, list(self._pages)

    def wait_for_change(self, last_revision, timeout):
        """Block until the revision advances past ``last_revision`` or timeout.

        Returns ``(revision, pages)`` — unchanged if it timed out.
        """
        with self._cond:
            if self._revision == last_revision:
                self._cond.wait(timeout)
            return self._revision, list(self._pages)


monitor_state = MonitorState()
