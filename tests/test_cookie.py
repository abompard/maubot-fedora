from unittest import mock

import httpx
import pytest

import fedora


def _mock_user(respx_mock, username):
    respx_mock.get(
        "http://fasjson.example.com/v1/search/users/",
        params={"ircnick__exact": f"matrix://example.com/{username}"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={"result": [{"username": username}]},
        )
    )
    respx_mock.get(f"http://fasjson.example.com/v1/users/{username}/").mock(
        return_value=httpx.Response(
            200,
            json={"result": {"username": username}},
        )
    )


async def test_cookie_give(bot, plugin, respx_mock):
    _mock_user(respx_mock, "dummy")
    _mock_user(respx_mock, "foobar")
    respx_mock.get(
        "http://bodhi.example.com/releases/",
        params={"state": "current"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "releases": [
                    {
                        "name": "F38",
                        "long_name": "Fedora 38",
                        "version": "38",
                        "id_prefix": "FEDORA",
                        "eol": "2024-05-14",
                    },
                    {
                        "name": "F37",
                        "long_name": "Fedora 37",
                        "version": "37",
                        "id_prefix": "FEDORA",
                        "eol": "2023-11-14",
                    },
                    {
                        "name": "F38C",
                        "long_name": "Fedora 38 Containers",
                        "version": "38",
                        "id_prefix": "FEDORA-CONTAINER",
                        "eol": "2024-05-14",
                    },
                ],
                "page": 1,
                "pages": 1,
                "rows_per_page": 20,
                "total": 13,
            },
        )
    )
    await bot.send("foobar++")
    assert len(bot.sent) == 1
    assert bot.sent[0].content.body == "foobar has 1 cookie(s)"


@pytest.mark.parametrize(
    "body,html,username",
    [
        ("foobar++", None, "foobar"),
        (
            "Foo Bar++",
            '<a href="https://matrix.to/#/@foobar:example.com">Foo Bar</a>++',
            "@foobar:example.com",
        ),
        (
            "Foo Bar:++",
            '<a href="https://matrix.to/#/@foobar:example.com">Foo Bar</a>:++',
            "@foobar:example.com",
        ),
        (
            "Foo Bar: ++",
            '<a href="https://matrix.to/#/@foobar:example.com">Foo Bar</a>: ++',
            "@foobar:example.com",
        ),
        ("do a foobar++ now", None, None),
        ("foobar++ well done!", None, "foobar"),
    ],
)
async def test_cookie_parse(bot, plugin, monkeypatch, body, html, username):
    give = mock.AsyncMock()
    monkeypatch.setattr(fedora.cookie.CookieHandler, "give", give)
    await bot.send(body, html=html)
    if username is None:
        give.assert_not_called()
    else:
        give.assert_called_once()
        assert give.call_args[0][1] == username


async def test_cookie_give_twice(bot, plugin, respx_mock, db):
    _mock_user(respx_mock, "dummy")
    _mock_user(respx_mock, "foobar")
    respx_mock.get(
        "http://bodhi.example.com/releases/",
        params={"state": "current"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "releases": [
                    {
                        "version": "38",
                        "id_prefix": "FEDORA",
                        "eol": "2024-05-14",
                    },
                ],
            },
        )
    )
    await db.execute(
        "INSERT INTO cookies (from_user, to_user, release) " "VALUES ('dummy', 'foobar', '38')"
    )
    await bot.send("foobar++")
    assert len(bot.sent) == 1
    assert (
        bot.sent[0].content.body
        == "You have already given cookies to foobar during the F38 timeframe"
    )
