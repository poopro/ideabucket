import asyncio
from types import SimpleNamespace

import pytest
from telegram.ext import ApplicationHandlerStop

from bot import config
from bot.main import enforce_owner


def test_telegram_owner_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "TELEGRAM_OWNER_USER_ID", 123)
    owner = SimpleNamespace(effective_user=SimpleNamespace(id=123))
    stranger = SimpleNamespace(effective_user=SimpleNamespace(id=999))

    asyncio.run(enforce_owner(owner, None))
    with pytest.raises(ApplicationHandlerStop):
        asyncio.run(enforce_owner(stranger, None))
