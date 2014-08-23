"""
    Deals with multipart POST requests.

    The code is adapted from the recipe found at :
    http://code.activestate.com/recipes/146306/
    No author name was given.

    Author : Alexis Mignon (c)
    email  : alexis.mignon@gmail.Com
    Date   : 06/08/2011

"""

import mimetypes

from tornado.gen import coroutine, Return
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from tornado_flickrapi import config


@coroutine
def posturl(url, fields, files):
    try:
        response = yield post_multipart(url, fields, files)
    except Exception as e:
        print e
        raise e
    raise Return(response)


@coroutine
def post_multipart(url, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.

    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)

    headers = {"Content-Type": content_type, 'content-length': str(len(body))}

    http_client = AsyncHTTPClient(io_loop=config["io_loop"])

    # use libcurl if it's available
    try:
        import pycurl
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    except Exception:
        pass

    request = HTTPRequest(url, "POST", headers=headers, body=body, validate_cert=False)
    try:
        response = yield http_client.fetch(request)
    except Exception as e:
        raise e

    raise Return(response)


def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.

    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        filename = filename.encode("utf8")
        L.append('--' + BOUNDARY)
        L.append(
            'Content-Disposition: form-data; name="%s"; filename="%s"' % (
                key, filename
            )
        )
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'