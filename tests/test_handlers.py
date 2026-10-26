from libs.handler import discord_handler, telegram_handler


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.text = str(body)

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


def patch_post(monkeypatch, module, response):
    monkeypatch.setattr(
        module.requests, "post", lambda *args, **kwargs: response
    )


def test_telegram_reads_retry_after(monkeypatch):
    patch_post(
        monkeypatch,
        telegram_handler,
        FakeResponse(429, {"ok": False, "parameters": {"retry_after": 7}}),
    )
    handler = telegram_handler.TelegramHandler()

    assert handler.send_message("1", "hi") is False
    assert handler.last_retry_after == 7


def test_discord_reads_retry_after(monkeypatch):
    patch_post(
        monkeypatch, discord_handler, FakeResponse(429, {"retry_after": 1.5})
    )
    handler = discord_handler.DiscordHandler()

    assert handler.send_message("https://hook", "hi") is False
    assert handler.last_retry_after == 1.5


def test_retry_after_is_none_when_body_is_not_json(monkeypatch):
    patch_post(
        monkeypatch, discord_handler, FakeResponse(429, ValueError("html"))
    )
    handler = discord_handler.DiscordHandler()

    handler.send_message("https://hook", "hi")

    assert handler.last_retry_after is None
