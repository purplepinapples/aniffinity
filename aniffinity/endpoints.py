"""aniffinity animelist endpoints."""


import re
import time
import warnings

import json_api_doc
import requests

from .const import DEFAULT_SERVICE, ENDPOINT_URLS, GRAPHQL_QUERY
from .exceptions import (
    InvalidUserError, NoAffinityError,
    RateLimitExceededError
)


TOO_MANY_REQUESTS = requests.codes.TOO_MANY_REQUESTS


def _resolve_service(user, service=None):
    """
    Resolve the `user` and `service` into "proper" values.

    As these params can take different types and formats, this
    function resolves all that to return just the username, and the
    full name of the service to use.

    :param user: A user
    :type user: str or tuple
    :param service: The service to use. If no value is specified
        for this param, specify the service in the ``user`` param,
        either as part of a url regex, or in a tuple
    :type service: str or None
    :return: (username, service)
    :rtype: tuple
    """
    username = None
    service_name_resolved = None

    if service:
        # `service` already specified so we don't need to do much work
        username = user
        service = service.upper()

        if service in _services:
            # Fastest option - service name fully specified so no
            # need to do any more work
            service_name_resolved = service
        else:
            # Check aliases to see which service is intended to be used
            for service_name, service_data in _services.items():
                if service in service_data["aliases"]:
                    service_name_resolved = service_name
                    break
            else:
                raise InvalidUserError("Invalid service name")

    elif type(user) is str:
        # `user` should be a url regex then, we just need to figure out
        # which service the regex matches
        for service_name, service_data in _services.items():
            match = re.search(service_data["url_regex"], user, re.I)

            if match:
                username = match.group(1)
                service_name_resolved = service_name
                break
        else:
            # Maybe it's just a URL and we don't have an endpoint for that
            # particular service. Check this before assuming anything else.
            if user.startswith("http"):
                raise InvalidUserError("Invalid service URL")

            # `user` may just be the username, so let's assume that and
            # use the default service.
            warnings.warn("No service has been specified, so assuming the "
                          "default '{}'. To stop this warning from appearing "
                          "again, please specify a service to use."
                          .format(DEFAULT_SERVICE), Warning, stacklevel=3)
            username = user
            service_name_resolved = DEFAULT_SERVICE

    # If `user` is a tuple as `(username, service)`
    elif isinstance(user, tuple) and len(user) == 2:
        # Unpack the tuple and pass the values back to this function.
        # Can't see anything going wrong with this... [](#yuishrug)
        return _resolve_service(*user)

    # Incorrect usage
    else:
        raise InvalidUserError("Invalid usage - check your `user` "
                               "and `service` values")

    return username, service_name_resolved


def _main(user, service=None):
    """
    Determine which endpoint to use and return a users' scores from that.

    :param user: A user
    :type user: str or tuple
    :param service: The service to use. If no value is specified
        for this param, specify the service in the ``user`` param,
        either as part of a url regex, or in a tuple
    :type service: str or None
    :return: Mapping of ``id`` to ``score``
    :rtype: dict
    """
    # Should be fine doing this.
    # If we've already passed the data to `_resolve_service` and passed
    # the result back in, it'll just throw the info back to us
    username, service = _resolve_service(user, service)

    # We don't need to worry about invalid services here, as
    # `figure_out_service` will raise the exception itself if it is invalid.
    service_data = _services.get(service)
    return service_data["endpoint"](username)


def anilist(username):
    """
    Retrieve a users' animelist scores from AniList.

    Only anime scored > 0 will be returned, and all
    PTW entries are ignored, even if they are scored.

    :param str username: AniList username
    :return: Mapping of ``id`` to ``score``
    :rtype: dict
    """
    params = {
        "query": GRAPHQL_QUERY,
        "variables": {"userName": username}
    }

    resp = requests.request("POST", ENDPOINT_URLS.ANILIST, json=params)

    if resp.status_code == TOO_MANY_REQUESTS:  # pragma: no cover
        raise RateLimitExceededError("AniList rate limit exceeded")

    # TODO: Handling for stuff
    # TODO: Consistency vars and stuff

    mlc = resp.json()["data"]["MediaListCollection"]

    if not mlc:
        # Is this the only reason for not having anything in the MLC?
        raise InvalidUserError("User `{}` does not exist on AniList"
                               .format(username))

    scores = {}

    for lst in mlc["lists"]:
        entries = lst["entries"]

        for entry in entries:
            id = str(entry["media"]["idMal"])
            score = entry["score"]

            if score > 0:
                scores[id] = score

    if not len(scores):
        raise NoAffinityError("User `{}` hasn't rated any anime on AniList"
                              .format(username))

    return scores


def kitsu(user_slug_or_id):
    """
    Retrieve a users' animelist scores from Kitsu.

    Only anime scored > 0 will be returned, and all
    PTW entries are ignored, even if they are scored.

    :param str user_slug_or_id: Kitsu user slug or user id
    :return: Mapping of ``id`` to ``score``
    :rtype: dict
    """
    if not user_slug_or_id.isdigit():
        # Username is the "slug". The API is incapable of letting us pass
        # a slug filter to the `library-entries` endpoint, so we need to
        # get the user id first...
        # TODO: Tidy this up
        user_id = requests.request(
            "GET",
            "https://kitsu.io/api/edge/users",
            params={"filter[slug]": user_slug_or_id}
        ).json()["data"]
        if not user_id:
            raise InvalidUserError("User `{}` does not exist on Kitsu"
                                   .format(user_slug_or_id))
        user_id = user_id[0]["id"]  # assume it's the first one, idk
    else:
        # Assume that if the username is all digits, then the user id is
        # passed so we can just send this straight into `library-entries`
        user_id = user_slug_or_id

    params = {
        "fields[anime]": "id,mappings",
        # TODO: Find a way to specify username instead of user_id.
        "filter[user_id]": user_id,
        "filter[kind]": "anime",
        "filter[status]": "completed,current,dropped,on_hold",
        "include": "anime,anime.mappings",
        "page[offset]": "0",
        "page[limit]": "500"
    }

    entries = []
    next_url = ENDPOINT_URLS.KITSU
    while next_url:
        resp = requests.request("GET", next_url, params=params)

        # TODO: Handle invalid username, other exceptions, etc
        if resp.status_code == TOO_MANY_REQUESTS:  # pragma: no cover
            raise RateLimitExceededError("Kitsu rate limit exceeded")

        json = resp.json()

        # The API silently fails if the user id is invalid,
        # which is a PITA, but hey...
        if not json["data"]:
            raise InvalidUserError("User `{}` does not exist on Kitsu"
                                   .format(user_slug_or_id))

        entries += json_api_doc.parse(json)

        # HACKISH
        # params built into future `next_url`s, bad idea to keep existing ones
        params = {}
        next_url = json["links"].get("next")

    scores = {}
    for entry in entries:
        # Our request returns mappings with various services, we need
        # to find the MAL one to get the MAL id to use.
        mappings = entry["anime"]["mappings"]
        for mapping in mappings:
            if mapping["externalSite"] == "myanimelist/anime":
                id = mapping["externalId"]
                break
        else:
            # Eh, if there isn't a MAL mapping, then the entry probably
            # doesn't exist there. Not much we can do if that's the case...
            continue

        score = entry["ratingTwenty"]

        # Why does this API do `score == None` when it's not rated?
        # Whatever happened to 0?
        if score is not None:
            scores[id] = score

    if not len(scores):
        raise NoAffinityError("User `{}` hasn't rated any anime on Kitsu"
                              .format(user_slug_or_id))

    return scores


def myanimelist(username):
    """
    Retrieve a users' animelist scores from MyAnimeList.

    Only anime scored > 0 will be returned, and all
    PTW entries are ignored, even if they are scored.

    :param str username: MyAnimeList username
    :return: Mapping of ``id`` to ``score``
    :rtype: dict
    """
    params = {
        "status": "7",  # all entries
        "offset": 0
    }

    scores = {}

    # This endpoint only returns 300 items at a time :( #BringBackMalAppInfo
    list_entries = 1
    while list_entries > 0:
        resp = requests.request(
            "GET",
            ENDPOINT_URLS.MYANIMELIST.format(username=username),
            params=params
        )
        
        # sleep to make sure we don't exceed rate limit
        time.sleep(2)
        
        if resp.status_code == TOO_MANY_REQUESTS:  # pragma: no cover
            raise RateLimitExceededError("MyAnimeList rate limit exceeded")

        json = resp.json()
        if "errors" in json:
            # TODO: Better error handling
            raise InvalidUserError("User `{}` does not exist on MyAnimeList"
                                   .format(username))

        for entry in json:
            if entry["status"] == 6:
                # Entry in PTW, skip
                continue

            id = str(entry["anime_id"])
            score = entry["score"]

            if score > 0:
                scores[id] = score
      
        list_entries = len(json)
        params["offset"] += 300

    if not len(scores):
        raise NoAffinityError("User `{}` hasn't rated any anime on MyAnimeList"
                              .format(username))

    return scores


# We can't move this to `.const` as referencing the endpoints from there
# will get pretty messy...
# TODO: Move the `ENDPOINT_URLS here as well???
_services = {
    "ANILIST": {
        "aliases": {"AL", "A"},
        "url_regex": r"^https?://anilist\.co/user/([a-z0-9_-]+)(?:\/(?:animelist)?)?$",  # noqa: E501
        "endpoint": anilist
    },
    "KITSU": {
        "aliases": {"K"},
        "url_regex": r"^https?://kitsu\.io/users/([a-z0-9_-]+)(?:/(?:library(?:\?media=anime)?)?)?$",  # noqa: E501
        "endpoint": kitsu
    },
    "MYANIMELIST": {
        "aliases": {"MAL", "M"},
        "url_regex": r"^https?://myanimelist\.net/(?:profile|animelist)/([a-z0-9_-]+)/?(?:\?status=\d)?",  # noqa: E501
        "endpoint": myanimelist
    }
}
