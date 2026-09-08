"""Exact-identity Discord DM transport for Sir Loke SL-01."""

from __future__ import annotations

import logging
from collections import deque

import discord

from markeitech.sir_loke.config import DiscordRuntimeConfig
from markeitech.sir_loke.conversation import SirLokeConversation

_LOG = logging.getLogger(__name__)


class SirLokeDiscordClient(discord.Client):
    def __init__(
        self,
        config: DiscordRuntimeConfig,
        conversation: SirLokeConversation,
    ) -> None:
        intents = discord.Intents.none()
        intents.dm_messages = True
        super().__init__(
            intents=intents,
            application_id=config.application_id,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self._config = config
        self._conversation = conversation
        self._identity_verified = False
        self._failure_reason: str | None = None
        self._recent_message_ids: deque[int] = deque(
            maxlen=config.maximum_recent_message_ids
        )
        self._recent_message_id_set: set[int] = set()

    @property
    def identity_verified(self) -> bool:
        return self._identity_verified

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason

    async def on_ready(self) -> None:
        if self.user is None or self.user.id != self._config.application_id:
            self._failure_reason = "Discord application identity mismatch"
            _LOG.error("Discord application identity does not match configured SL-01 identity")
            await self.close()
            return
        self._identity_verified = True
        _LOG.info(
            "Sir Loke SL-01 Discord transport is ready application_id=%s",
            self._config.application_id,
        )

    async def on_message(self, message: discord.Message) -> None:
        if not self._admitted_identity(message):
            return
        if not self._admit_message_id(message.id):
            return
        if (
            message.attachments
            or message.embeds
            or message.stickers
            or message.components
            or message.poll is not None
        ):
            reply = await self._conversation.reject_non_text()
            delivered = False
            try:
                await message.channel.send(
                    reply.content,
                    allowed_mentions=discord.AllowedMentions.none(),
                    suppress_embeds=True,
                )
                delivered = True
            finally:
                await self._conversation.record_delivery(reply, delivered=delivered)
            return
        reply = await self._conversation.handle(message.content)
        delivered = False
        try:
            await message.channel.send(
                reply.content,
                allowed_mentions=discord.AllowedMentions.none(),
                suppress_embeds=True,
            )
            delivered = True
        finally:
            await self._conversation.record_delivery(reply, delivered=delivered)

    def _admitted_identity(self, message: discord.Message) -> bool:
        return (
            self._identity_verified
            and message.guild is None
            and isinstance(message.channel, discord.DMChannel)
            and message.channel.id == self._config.dm_channel_id
            and message.author.id == self._config.user_id
            and not message.author.bot
            and message.webhook_id is None
        )

    def _admit_message_id(self, message_id: int) -> bool:
        if message_id in self._recent_message_id_set:
            return False
        if len(self._recent_message_ids) == self._recent_message_ids.maxlen:
            expired = self._recent_message_ids.popleft()
            self._recent_message_id_set.remove(expired)
        self._recent_message_ids.append(message_id)
        self._recent_message_id_set.add(message_id)
        return True
