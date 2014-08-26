"""
    Upload API for Flickr.
    It is separated since it requires different treatments than
    the usual API.

    Two functions are provided:

    - upload (supporting both sync and async modes)
    - replace (presently not working)

    Author: Dmitriy Bryndin
    email: bryndin@gmail.com
    Date:  08/24/2014

    Author: Alexis Mignon (c)
    email: alexis.mignon@gmail.com
    Date:  06/08/2011
"""

import os
import logging

from xml.etree import ElementTree

from tornado.gen import coroutine, Return
from tornado.ioloop import PeriodicCallback
from tornado.concurrent import Future

from flickrerrors import FlickrError, FlickrAPIError
from objects import Photo
import auth
import multipart


UPLOAD_URL = "https://api.flickr.com/services/upload/"
REPLACE_URL = "https://api.flickr.com/services/replace/"

_futures = {}
log = logging.getLogger("tornado.application")


def format_dict(d):
    d_ = {}
    for k, v in d.iteritems():
        if isinstance(v, bool):
            v = int(v)
        elif isinstance(v, unicode):
            v = v.encode("utf8")
        if isinstance(k, unicode):
            k = k.encode("utf8")
        v = str(v)
        d_[k] = v
    return d_


@coroutine
def post(url, auth_handler, photo_file, **kwargs):
    kwargs = format_dict(kwargs)
    kwargs["api_key"] = auth_handler.key

    params = auth_handler.complete_parameters(url, kwargs).parameters

    fields = params.items()

    files = [("photo", os.path.basename(photo_file), open(photo_file).read())]

    try:
        response = yield multipart.posturl(url, fields, files)
    except Exception as e:
        raise e

    if response.code != 200:
        raise FlickrError("HTTP Error %i: %s" % (response.code, response.body))
    
    r = ElementTree.fromstring(response.body)
    if r.get("stat") != 'ok':
        err = r[0]
        raise FlickrAPIError(int(err.get("code")), err.get("msg"))
    raise Return(r)


@coroutine
def upload(**kwargs):
    """
    Authentication:

        This method requires authentication with 'write' permission.

    Arguments:
        photo_file
            The file to upload.
        title (optional)
            The title of the photo.
        description (optional)
            A description of the photo. May contain some limited HTML.
        tags (optional)
            A space-separated list of tags to apply to the photo.
        is_public, is_friend, is_family (optional)
            Set to 0 for no, 1 for yes. Specifies who can view the photo.
        safety_level (optional)
            Set to 1 for Safe, 2 for Moderate, or 3 for Restricted.
        content_type (optional)
            Set to 1 for Photo, 2 for Screenshot, or 3 for Other.
        hidden (optional)
            Set to 1 to keep the photo in global search results, 2 to hide
            from public searches.
        async
            set to 1 for async mode, 0 for sync mode

    """
    if "async" not in kwargs:
        kwargs["async"] = False

    if auth.AUTH_HANDLER is None:
        raise FlickrError("Not authenticated")

    photo_file = kwargs.pop("photo_file")
    try:
        resp_body = yield post(UPLOAD_URL, auth.AUTH_HANDLER, photo_file, **kwargs)
    except Exception as e:
        log.error("Failed to upload %s" % photo_file)
        raise e

    t = resp_body[0]
    if t.tag == 'photoid':
        # sync mode, got a photo
        raise Return(Photo(id=t.text,
                           editurl='https://www.flickr.com/photos/upload/edit/?ids=' + t.text))
    elif t.tag == 'ticketid':
        # async mode, got a ticket
        if not _futures:
            _periodic_checks.start()

        _futures[t.text] = Future()
        try:
            yield _futures[t.text]
        except Exception as e:
            raise e

        raise Return(Photo(id=t.text,
                           editurl='https://www.flickr.com/photos/upload/edit/?ids=' + t.text))
    else:
        raise FlickrError("Unexpected tag: %s" % t.tag)


def replace(**kwargs):
    """
     Authentication:

        This method requires authentication with 'write' permission.

        For details of how to obtain authentication tokens and how to sign
        calls, see the authentication api spec. Note that the 'photo' parameter
        should not be included in the signature. All other POST parameters
        should be included when generating the signature.

    Arguments:

        photo_file
            The file to upload.
        photo_id
            The ID of the photo to replace.
        async (optional)
            Photos may be replaced in async mode, for applications that
            don't want to wait around for an upload to complete, leaving
            a socket connection open the whole time. Processing photos
            asynchronously is recommended. Please consult the documentation
            for details.

    """
    if "async" not in kwargs:
        kwargs["async"] = False
    if "photo" in kwargs:
        kwargs["photo_id"] = kwargs.pop("photo").id

    photo_file = kwargs.pop("photo_file")

    try:
        resp_body = yield post(REPLACE_URL, auth.AUTH_HANDLER, photo_file, **kwargs)
    except Exception as e:
        raise e

    t = resp_body[0]
    if t.tag == 'photoid':
        # sync mode, got a photo
        raise Return(Photo(id=t.text,
                           editurl='https://www.flickr.com/photos/upload/edit/?ids=' + t.text))
    elif t.tag == 'ticketid':
        # async mode, got a ticket
        if not _futures:
            _periodic_checks.start()

        _futures[t.text] = Future()
        try:
            yield _futures[t.text]
        except Exception as e:
            raise e

        raise Return(Photo(id=t.text,
                           editurl='https://www.flickr.com/photos/upload/edit/?ids=' + t.text))
    else:
        raise FlickrError("Unexpected tag: %s" % t.tag)


@coroutine
def _check_tickets():
    try:
        tickets = yield Photo.checkUploadTickets(_futures.keys())
    except Exception as e:
        print e
        raise e
    for t in tickets:
        f = _futures[t.id]
        del _futures[t.id]
        if not _futures:
            _periodic_checks.stop()

        if t.get("complete", 0) == 1:
            # completed successfully
            f.set_result()
        elif t.get("complete", 0) == 2:
            # ticket failed, problem converting photo?
            f.set_exception(FlickrError("Ticket %s failed" % t.id))
        elif t.get("invalid", 0) == 1:
            # ticket not found
            f.set_exception(FlickrError("Ticket %s not found" % t.id))


CHECK_PERIOD = 2*1000   # how often check if tickets are ready
_periodic_checks = PeriodicCallback(_check_tickets, CHECK_PERIOD)
