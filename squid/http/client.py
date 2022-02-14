from typing import Any, Dict, Optional, Sequence
from discord.http import Route, json_or_text
from discord import utils, File
from discord.errors import HTTPException, Forbidden, NotFound, DiscordServerError
from urllib.parse import quote as _uriquote
import sys
from requests.models import Response
import requests
import json
import time
from discord.http import HTTPClient as _HTTPClient


def json_or_text(response: requests.Response):
    text = response.text
    try:
        if response.headers["content-type"] == "application/json":
            return json.loads(text)
    except KeyError:
        # Thanks Cloudflare
        pass

    return text


class HttpClient(_HTTPClient):
    def __init__(self, token: str, *, session: requests.Session = None):
        self.token = token

        self.__session = session or requests.Session()
        # implement locks latr  # self._locks = weakref.WeakValueDictionary()

        user_agent = "(https://github.com/Squidtoon99/command-handler {0}) Python/{1[0]}.{1[1]} requests/{2}"
        self.user_agent: str = user_agent.format(
            "1.0", sys.version_info, requests.__version__
        )

    def request(
        self,
        route: Route,
        *,
        files: Optional[Sequence[File]] = [],
        **kwargs: Any,
    ):
        bucket = route.bucket
        method = route.method
        url = route.url

        headers: Dict[str, str] = {
            "User-Agent": self.user_agent,
        }

        if self.token is not None:
            headers["Authorization"] = f"Bot {self.token}"

        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
            kwargs["data"] = utils._to_json(kwargs.pop("json"))

        try:
            reason = kwargs.pop("reason")
        except KeyError:
            pass
        else:
            headers["X-Audit-Log-Reason"] = _uriquote(reason, safe="/ ")

        kwargs["headers"] = headers

        for tries in range(5):
            if files:
                for f in files:
                    f.reset(seek=tries)

            try:
                response: Response = self.__session.request(method, url, **kwargs)

                data = json_or_text(response)
                remaining = response.headers.get("X-Ratelimit-Remaining")
                if remaining == "0" and response.status_code != 429:
                    pass
                    # we've depleted our current bucket
                    # delta = utils._parse_ratelimit_header(response, use_clock=self.use_clock)
                    # # _log.debug('A rate limit bucket has been exhausted (bucket: %s, retry: %s).', bucket, delta)
                    # maybe_lock.defer()
                    # self.loop.call_later(delta, lock.release)

                # the request was successful so just return the text/json
                if 300 > response.status_code >= 200:
                    return data

                # we are being rate limited
                if response.status_code == 429:
                    if not response.headers.get("Via") or isinstance(data, str):
                        # Banned by Cloudflare more than likely.
                        raise HTTPException(response, data)

                    fmt = 'We are being rate limited. Retrying in %.2f seconds. Handled under the bucket "%s"'

                    # sleep a bit
                    retry_after: float = data["retry_after"]
                    # _log.warning(fmt, retry_after, bucket)

                    # check if it's a global rate limit
                    # is_global = data.get("global", False)
                    # if is_global:
                    # _log.warning(
                    #     "Global rate limit has been hit. Retrying in %.2f seconds.",
                    #     retry_after,
                    # )
                    #     self._global_over.clear()

                    time.sleep(retry_after)
                    # _log.debug("Done sleeping for the rate limit. Retrying...")

                    # release the global lock now that the
                    # global rate limit has passed
                    # if is_global:
                    #     self._global_over.set()
                    # _log.debug("Global rate limit is now over.")

                    # continue

                # we've received a 500, 502, or 504, unconditional retry
                if response.status_code in {500, 502, 504}:
                    time.sleep(0.5)  # i'm not made of money here
                    continue

                # the usual error cases
                if response.status_code == 403:
                    raise Forbidden(response, data)
                elif response.status_code == 404:
                    raise NotFound(response, data)
                elif response.status_code >= 500:
                    raise DiscordServerError(response, data)
                else:
                    raise HTTPException(response, data)

            # This is handling exceptions from the request
            except OSError as e:
                # Connection reset by peer
                if tries < 4 and e.errno in (54, 10054):
                    time.sleep(tries * 0.5)
                    continue
                raise

        if response is not None:
            # We've run out of retries, raise.
            if response.status_code >= 500:
                raise DiscordServerError(response, data)

            raise HTTPException(response, data)

        raise RuntimeError("Unreachable code in HTTP handling")

    def get_from_cdn(self, url: str) -> bytes:
        r = self.__session.get(url)

        if r.status_code == 200:
            return r.content
        elif r.status_code == 404:
            raise NotFound(r, "asset not found")
        elif r.status_code == 403:
            raise Forbidden(r, "access forbidden")
        else:
            raise HTTPException(r, "failed getting asset")
