import sys

from tornado.ioloop import IOLoop
from tornado.gen import coroutine

import tornado_flickr_api


@coroutine
def start():
    try:
        username = sys.argv[1]
        try:
            access_token = sys.argv[2]
            tornado_flickr_api.set_auth_handler(access_token)
        except IndexError:
            pass

        u = yield tornado_flickr_api.Person.findByUserName(username)
        ps = yield u.getPhotosets()

        for i, p in enumerate(ps):
            print i, p.title
    except IndexError:
        print "usage: python show_albums.py username [access_token_file]"
        print "Displays the list of photosets belonging to a user"


if __name__ == "__main__":
    IOLoop.instance().run_sync(start)