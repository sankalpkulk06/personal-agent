from typing import Optional

from twilio.rest import Client


class WhatsAppService:
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._client = Client(account_sid, auth_token)
        self._from_number = from_number

    def send_message(self, to: str, body: str) -> None:
        for chunk in self.split_message(body):
            self._client.messages.create(
                from_=self._from_number,
                to=to,
                body=chunk,
            )

    def send_media(self, to: str, media_url: str, caption: str = "") -> None:
        self._client.messages.create(
            from_=self._from_number,
            to=to,
            media_url=[media_url],
            body=caption,
        )

    def split_message(self, text: str, limit: int = 1600) -> list[str]:
        if len(text) <= limit:
            return [text]

        chunks = []
        while len(text) > limit:
            boundary = text.rfind(". ", 0, limit)
            if boundary != -1:
                chunks.append(text[: boundary + 2].strip())
                text = text[boundary + 2 :].strip()
            else:
                word_boundary = text.rfind(" ", 0, limit)
                cut = word_boundary if word_boundary != -1 else limit
                chunks.append(text[:cut].strip())
                text = text[cut:].strip()

        if text:
            chunks.append(text)

        return chunks
