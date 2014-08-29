import logging

from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.gen import Task, coroutine, Return

from tornado_flickrapi import config


log = logging.getLogger("tornado.application")


@coroutine
def fetch(request):
    io_loop = config["io_loop"]
    starting_timeout = config.get("starting_timeout", 0.5)
    max_timeout = config.get("max_timeout", 0)

    http_client = AsyncHTTPClient(io_loop)

    # use libcurl if it's available
    try:
        import pycurl
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    except Exception:
        pass

    timeout = starting_timeout
    while True:
        try:
            response = yield http_client.fetch(request)
            break
        except HTTPError as e:
            log.debug("Retrying HTTP exception: %s\n" % e +
                      "request headers: %s\n" % request.headers +
                      "request body: %s\n" % request.body +
                      "timeout: %.1f sec" % timeout,
                      exc_info=True)
            yield Task(io_loop.call_later, timeout)
            timeout *= 2
            if timeout > max_timeout:
                raise e
        except Exception as e:
            log.debug("Exception: %s\n" % e +
                      "request headers: %s\n" % request.headers +
                      "request body: %s\n" % request.body,
                      exc_info=True)
            raise e

    raise Return(response)
