"""
    method_call module.

    This module is used to perform the calls to the REST interface.

    Author: Alexis Mignon (c)
    e-mail: alexis.mignon@gmail.com
    Date: 06/08/2011

"""
import urllib2
import urllib
import hashlib
import json
import logging

from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from tornado.gen import Task, coroutine, Return
from tornado.ioloop import IOLoop

from . import keys
from .flickrerrors import FlickrError, FlickrAPIError
from .cache import SimpleCache
from tornado_flickrapi import config

REST_URL = "https://api.flickr.com/services/rest/"

CACHE = None

log = logging.getLogger("tornado.application")


def enable_cache(cache_object=None):
    """ enable caching
    Parameters:
    -----------
    cache_object: object, optional
        A Django compliant cache object. If None (default), a SimpleCache
        object is used.
    """
    global CACHE
    CACHE = cache_object or SimpleCache()


def disable_cache():
    """Disable cachine capabilities
    """
    global CACHE
    CACHE = None


@coroutine
def send_request(url, data=None, starting_timeout=0.5, max_timeout=0):
    """Sends an async http request."""
    io_loop = config["io_loop"]
    http_client = AsyncHTTPClient(io_loop)

    # use libcurl if it's available
    try:
        import pycurl
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    except Exception:
        pass

    request = HTTPRequest(url, method="POST", body=data) if data else HTTPRequest(url)

    timeout = starting_timeout
    while True:
        try:
            response = yield http_client.fetch(request)
            break
        except HTTPError as e:
            log.debug("Retrying HTTP exception: %s\n" % e +
                      "request: %s\n" % request,
                      exc_info=True)
            yield Task(io_loop.call_later, timeout)
            timeout *= 2
            if timeout > max_timeout:
                raise e
        except Exception as e:
            log.debug("Exception: %s\n" % e +
                      "request: %s\n" % request,
                      exc_info=True)
            raise e

    raise Return(response)


@coroutine
def call_api(api_key=None, api_secret=None, auth_handler=None,
             needssigning=False, request_url=REST_URL, raw=False, **args):
    """
        Performs the calls to the Flickr REST interface.

    Parameters:
        api_key:
            The API_KEY to use. If none is given and a auth_handler is used
            the key stored in the auth_handler is used, otherwise, the values
            stored in the `flickr_keys` module are used.
        api_secret:
            The API_SECRET to use. If none is given and a auth_handler is used
            the key stored in the auth_handler is used, otherwise, the values
            stored in the `flickr_keys` module are used.
        auth_handler:
            The authentication handler object to use to perform authentication.
        request_url:
            The url to the rest interface to use by default the url in REST_URL
            is used.
        raw:
            if True the default xml response from the server is returned. If
            False (default) a dictionnary built from the JSON answer is
            returned.
        args:
            the arguments to pass to the method.
    """

    if not api_key:
        if auth_handler is not None:
            api_key = auth_handler.key
        else:
            api_key = keys.API_KEY
    if not api_secret:
        if auth_handler is not None:
            api_secret = auth_handler.secret
        else:
            api_secret = keys.API_SECRET

    if not api_key or not api_secret:
        raise FlickrError("The Flickr API keys have not been set")

    clean_args(args)
    args["api_key"] = api_key
    if not raw:
        args["format"] = 'json'
        args["nojsoncallback"] = 1

    if auth_handler is None:
        if needssigning:
            query_elements = args.items()
            query_elements.sort()
            sig = keys.API_SECRET + ["".join(["".join(e) for e in query_elements])]
            m = hashlib.md5()
            m.update(sig)
            api_sig = m.digest()
            args["api_sig"] = api_sig
        data = urllib.urlencode(args)
    else:
        data = auth_handler.complete_parameters(url=request_url, params=args).to_postdata()

    if CACHE is None:
        try:
            resp = yield send_request(request_url, data)
        except Exception as e:
            raise e
    else:
        resp = CACHE.get(data)
        if resp is None:
            try:
                resp = yield send_request(request_url, data)
            except Exception as e:
                raise e
        if data not in CACHE:
            CACHE.set(data, resp)

    if raw:
        raise Return(resp)

    try:
        resp = json.loads(resp.body)
    except ValueError, e:
        print resp
        raise e

    if resp["stat"] != "ok":
        raise FlickrAPIError(resp["code"], resp["message"])

    resp = clean_content(resp)

    raise Return(resp)


def clean_content(d):
    """
    Cleans out recursively the keys comming from the JSON
    dictionnary.

    Namely: "_content" keys are replaces with their associated
        values if they are the only key of the dictionnary. Other
        wise they are replaces by a "text" key with the same value.
    """
    if isinstance(d, dict):
        d_clean = {}
        if len(d) == 1 and "_content" in d:
            return clean_content(d["_content"])
        for k, v in d.iteritems():
            if k == "_content":
                k = "text"
            d_clean[k] = clean_content(v)
        return d_clean
    elif isinstance(d, list):
        return [clean_content(i) for i in d]
    else:
        return d


def clean_args(args):
    """
        Reformat the arguments.
    """
    for k, v in args.items():
        if isinstance(v, bool):
            args[k] = int(v)
