# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Codrago, 2024-2025
# This file is a part of Heroku Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import aiohttp
import logging
import re
import os
import random
import typing

from urllib.parse import unquote

from herokutl.errors.rpcerrorlist import YouBlockedUserError
from herokutl.tl.functions.contacts import UnblockRequest
from herokutl.tl.functions.messages import RequestWebViewRequest

from .. import utils
from .. import main
from .._internal import fw_protect
from .types import InlineUnit

if typing.TYPE_CHECKING:
    from ..inline.core import InlineManager

logger = logging.getLogger(__name__)

headers = {
  "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
  "accept": "application/json, text/javascript, */*; q=0.01",
  "referer": "https://webappinternal.telegram.org/botfather",
  "cookie": "stel_ln=ru",
}
HASH_PATTERN = re.compile(r"Main\.init\('([0-9a-f]{18})'\);")
BOT_ID_PATTERN = (
    r"<a class=\"tm-row tm-row-link\" href=\"/botfather/bot/(\d+)\">"
    r"<img class=\"tm-row-pic tm-row-pic-user\" src=\"https:\/\/cdn4\.telesco\.pe\/file\/[A-Za-z0-9_-]+\.jpg\">"
    r"<div> <div class=\"tm-row-value\">((?:(?!<\/div>).)*)<\/div>"
    r"<div class=\"tm-row-description\">@{}</div> </div></a>"
)
BOT_BASE_PATTERN = re.compile(BOT_ID_PATTERN.format(r"\w*_[0-9a-zA-Z]{6}_bot"))


class TokenObtainment(InlineUnit):
    async def _get_webapp_session(self: "InlineManager", url: str) :
        session = aiohttp.ClientSession()
        params = unquote(url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
        base_url = url.split("?")[0]

        async with session.post(base_url + f"/api?hash=-", headers=headers, data={"_auth": params, "method": "auth"}) as resp:
            if resp.status != 200:
                logger.error("Error while getting Cookies to enter botfather webapp: resp%s", resp.status)
                raise RuntimeError("Getting Cookies failed")
        
        async with session.get(base_url, headers=headers) as resp:
            if resp.status != 200:
                logger.error("Error while getting hash: resp%s", resp.status)
                return RuntimeError("Getting api hash failed")
            text = await resp.text()
            _hash = re.search(HASH_PATTERN, text)
            if _hash:
                _hash = _hash.group(1)
            else:
                logger.error("Unexpected error while getting token")
                return False

        return (session, _hash)
        

    async def _main_token_manager(
        self: "InlineManager",
        action: int,
        revoke_token: bool = False,
        create_new_if_needed: bool = True,
        already_initialised: bool = True
    ) -> bool | None:
        url: str = (
            await self._client(RequestWebViewRequest(
                peer="@botfather",
                bot="@botfather",
                platform="android",
                from_bot_menu=False,
                url="https://webappinternal.telegram.org/botfather?")
            )
        ).url
        result = await self._get_webapp_session(url)
        
        if not result or isinstance(result, bool):
            logger.error("WebApp is not available now")
            return False

        session, _hash = result
        
        main_url = url.split("?")[0]
        try:
            if action == 1:
                return await self._assert_token(
                    session,
                    main_url,
                    _hash,
                    create_new_if_needed=create_new_if_needed,
                    revoke_token=revoke_token
                )
            elif action == 2:
                return await self._create_bot(session, main_url, _hash)
            elif action == 3:
                return await self._dp_revoke_token(
                    session,
                    main_url,
                    _hash,
                    already_initialised=already_initialised
                )
            elif action == 4:
                return await self._reassert_token(session, main_url, _hash)
        finally:
            await session.close()


    async def _create_bot(
        self: "InlineManager",
        session: aiohttp.ClientSession,
        url: str,
        _hash: str
    ):
        logger.info("User doesn't have bot, attempting creating new one")

        if self._db.get("heroku.inline", "custom_bot", False):
            username = self._db.get("heroku.inline", "custom_bot").strip("@")
            username = f"@{username}"
            try:
                await self._client.get_entity(username)
            except ValueError:
                pass
            else:
                uid = utils.rand(6)
                genran = "".join(random.choice(main.LATIN_MOCK))
                username = f"@{genran}_{uid}_bot"
        else:
            uid = utils.rand(6)
            genran = "".join(random.choice(main.LATIN_MOCK))
            username = f"@{genran}_{uid}_bot"

        for _ in range(5):
            data = {"username": username, "method": "checkBotUsername"}
            await fw_protect()

            async with session.post(url + f"/api?hash={_hash}", data=data, headers=headers) as resp:
                if resp.status != 200:
                    logger.error("Error while username check: resp%s", resp.status)
                    return False

                content = await resp.json()
            result = content.get("ok", False)

            if result:
                break

            uid = utils.rand(6)
            genran = "".join(random.choice(main.LATIN_MOCK))
            username = f"@{genran}_{uid}_bot"
        else:
            logger.error("You've got reached limit of tries while checking username")
            return False
        
        try:
            photo_b = open(f"{os.getcwd()}/assets/heroku.png", "rb").read()
            form = aiohttp.FormData()
            form.add_field(
                "photo",
                photo_b,
                content_type="image/jpeg",
                filename="photo.png"
            )
            form.add_field(
                "method",
                "uploadMedia"
            )
            form.add_field(
                "target",
                "bot_userpic"
            )
            async with session.post(url + f"/api?hash={_hash}", data=form, headers=headers) as resp:
                if resp.status != 200:
                    logger.error("Error while uploading bot userpic: resp%s", resp.status)
                    raise RuntimeError("Upload failed")
                content = await resp.json()
                photo_id = content["media"]["photo_id"]
        except (RuntimeError, KeyError):
            photo_id = ""
        
        data = {
            "title": f"🪐 Heroku {utils.get_version_raw()}"[:64],
            "username": username,
            "about": "",
            "userpic": photo_id,
            "method": "createBot"
        }
        await fw_protect()
        async with session.post(url + f"/api?hash={_hash}", data=data, headers=headers) as resp:
            if resp.status != 200:
                logger.error("Error while creating the bot: resp%s", resp.status)
                return False

            content = await resp.json()
            if not content.get("ok", False):
                logger.error(
                    "Error while creating the bot. "
                    "Maybe you've been banned or exceeded the limit: %s", content)
                return False
            # bot_id = content["bot_id"]

        return await self._assert_token(session, url, _hash, create_new_if_needed=False)

    async def _assert_token(
        self: "InlineManager",
        session: aiohttp.ClientSession,
        url: str,
        _hash: str,
        create_new_if_needed: bool = True,
        revoke_token: bool = False,
    ) -> bool:
        if self._token:
            return True

        logger.info("Bot token not found in db, attempting search in BotFather")

        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.error("Error while getting bot list: resp%s", resp.status)
                return False
            content = await resp.text()

        ids = None
        bot_id = None
            
        username = self._db.get("heroku.inline", "custom_bot", False)
        if username:
            ids = re.search(BOT_ID_PATTERN.format(username), content)
            
        else:
            ids = re.search(BOT_BASE_PATTERN, content)
            
        if ids:
            bot_id = ids.group(1)

        if bot_id:
            if revoke_token:
                async with session.post(
                    url + f"/api?hash={_hash}",
                    data={"bid": bot_id, "method": "revokeAccessToken"},
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        logger.error("Error while revoking token: resp%s", resp.status)
                        return False

                    token = (await resp.json())["token"]
            else:
                hdrs = headers.copy()
                hdrs.update(
                    {
                        "x-aj-referer": "https://webappinternal.telegram.org/botfather",
                        "x-requested-with": "XMLHttpRequest"
                    }
                )
                async with session.get(url + f"/bot/{bot_id}", headers=hdrs) as resp:
                    if resp.status != 200:
                        logger.error("Error while getting token: resp%s", resp.status)
                        return False
                    
                    text = (await resp.json())["h"]
                    token = re.search(r"(\d+:[A-Za-z0-9\-_]{35})", text)
                    token = token.group(1)

            self._db.set("heroku.inline", "bot_token", token)
            self._token = token

            for method, value in {
                "settings[inline]": "true",
                "settings[inph]": "user@heroku:~$",
                "settings[infdb]": "1"
            }.items():
                await fw_protect()

                async with session.post(
                    url + f"/api?hash={_hash}",
                    data={method: value, "bid": bot_id, "method": "changeSetting"},
                    headers=headers
                ):
                    if resp.status != 200:
                        logger.error("Error while changing bot inline settings: resp%s", resp.status)
                        return False

            return True

        return await self._create_bot(session, url, _hash) if create_new_if_needed else False

    async def _reassert_token(
        self: "InlineManager",
        session: aiohttp.ClientSession,
        url: str,
        _hash: str
    ):
        is_token_asserted = await self._assert_token(session, url, _hash, revoke_token=True)
        if not is_token_asserted:
            self.init_complete = False
        else:
            await self.register_manager(ignore_token_checks=True)

    async def _dp_revoke_token(
        self: "InlineManager",
        session: aiohttp.ClientSession,
        url: str,
        _hash: str,
        already_initialised: bool = True
    ):
        if already_initialised:
            await self._stop()
            logger.error("Got polling conflict. Attempting token revocation...")

        self._db.set("heroku.inline", "bot_token", None)
        self._token = None
        if already_initialised:
            asyncio.ensure_future(self._reassert_token(session, url, _hash))
        else:
            return await self._reassert_token(session, url, _hash)
        
    async def assert_token(
        self: "InlineManager",
        create_new_if_needed: bool = True,
        revoke_token: bool = False
    ):
        return await self._main_token_manager(
            1,
            create_new_if_needed=create_new_if_needed,
            revoke_token=revoke_token
        )
        
    async def create_bot(self: "InlineManager"):
        return await self._main_token_manager(2)

    async def dp_revoke_token(self: "InlineManager", already_initialised: bool = True):
        return await self._main_token_manager(3, already_initialised=already_initialised)

    async def reassert_token(self: "InlineManager"):
        return await self._main_token_manager(4)