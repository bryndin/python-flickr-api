import sys

from tornado.ioloop import IOLoop
from tornado.gen import coroutine

import flickr_api


@coroutine
def start():
    try:
        access_token = sys.argv[1]
        flickr_api.set_auth_handler(access_token)
    except IndexError:
        pass

    path = "publicdomain.large.png"
    try:
        photo1 = flickr_api.upload(photo_file=path, title="test1", safety_level=1,
                                   is_public=0, is_friend=0, is_family=0,
                                   content_type=1, hidden=2, async=1)
        photo2 = flickr_api.upload(photo_file=path, title="test2", safety_level=1,
                                   is_public=0, is_friend=0, is_family=0,
                                   content_type=1, hidden=2, async=1)
        photo3 = flickr_api.upload(photo_file=path, title="test3", safety_level=1,
                                   is_public=0, is_friend=0, is_family=0,
                                   content_type=1, hidden=2, async=1)
        yield [photo1, photo2, photo3]
    except Exception as e:
        raise e


if __name__ == "__main__":
    IOLoop.instance().run_sync(start)
