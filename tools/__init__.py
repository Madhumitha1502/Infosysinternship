"""
tools package
=============
Concrete, executable response actions used by the Response Agent.

Each tool is implemented as:
  1. A plain Python function `run(...)` containing the real logic
     (guarded by `settings.dry_run` so nothing destructive happens by
     default), and
  2. A LangChain `@tool`-decorated wrapper of the same function, so these
     actions can also be bound to a LangChain agent/executor if desired.

Import the individual modules for direct use, e.g.:
    from tools.block_ip import block_ip
"""

from tools.block_ip import block_ip
from tools.email_alert import send_email_alert
from tools.isolate_device import isolate_device
from tools.rate_limit import rate_limit

__all__ = ["block_ip", "isolate_device", "rate_limit", "send_email_alert"]
