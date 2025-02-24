import asyncio
import logging
from pathlib import Path

import aiohttp
import pytest_asyncio
from maubot.loader import PluginMeta
from maubot.standalone.loader import FileSystemLoader
from mautrix.util.async_db import Database
from mautrix.util.config import RecursiveDict
from mautrix.util.logging import TraceLogger
from ruamel.yaml import YAML

from fedora import Config, Fedora

from .bot import TestBot


@pytest_asyncio.fixture
async def bot():
    return TestBot()


@pytest_asyncio.fixture
async def db(tmp_path):
    db_path = tmp_path.joinpath("tests.db").as_posix()
    db = Database.create(
        f"sqlite:///{db_path}",
        upgrade_table=Fedora.get_db_upgrade_table(),
        log=logging.getLogger("db"),
    )
    await db.start()
    yield db
    await db.stop()


@pytest_asyncio.fixture
async def plugin(bot, db):
    base_path = Path(__file__).parent.parent
    yaml = YAML()
    with open(base_path.joinpath("maubot.yaml")) as fh:
        plugin_meta = PluginMeta.deserialize(yaml.load(fh.read()))
    with open(base_path.joinpath("base-config.yaml")) as fh:
        base_config = RecursiveDict(yaml.load(fh))
    test_config = {
        "fasjson_url": "http://fasjson.example.com",
        "pagureio_url": "http://pagure.example.com",
        "paguredistgit_url": "http://src.example.com",
        "controlroom": "controlroom",
    }
    config = Config(lambda: test_config, lambda: base_config, lambda c: None)
    loader = FileSystemLoader(base_path, plugin_meta)
    async with aiohttp.ClientSession() as http:
        instance = Fedora(
            client=bot.client,
            loop=asyncio.get_running_loop(),
            http=http,
            instance_id="tests",
            log=TraceLogger("test"),
            config=config,
            database=db,
            webapp=None,
            webapp_url=None,
            loader=loader,
        )
        await instance.internal_start()
        yield instance
