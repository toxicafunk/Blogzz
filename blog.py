#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os.path
import logging

#import pkg_resources
#pkg_resources.require("oauth")

import tornado.wsgi
import wsgiref.handlers

import blogzz.handlers as handlers

settings = {
    "blog_title": u"Movimiento y prop\u00F3sito",
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "ui_modules": {"Entry": handlers.EntryModule},
    "xsrf_cookies": True,
    "use_buzz": True,
}
application = tornado.wsgi.WSGIApplication([
    (r"/", handlers.HomeHandler),
    (r"/archive", handlers.ArchiveHandler),
    (r"/feed", handlers.FeedHandler),
    (r"/entry/([^/]+)", handlers.EntryHandler),
    (r"/compose", handlers.ComposeHandler),
    (r"/atomtest", handlers.AtomTestHandler),
    (r"/subhub", handlers.SubHubHandler),
    (r"/hubcallback", handlers.HubCallbackHandler),
], **settings)

def real_main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(msecs)03d %(levelname)-8s %(name)-8s %(message)s', datefmt='%H:%M:%S')
    #tornado.locale.load_translations(
    #    os.path.join(os.path.dirname(__file__), "translations"))
    wsgiref.handlers.CGIHandler().run(application)

def profile_main():
    # This is the main function for profiling
    # We've renamed our original main() above to real_main()
    import cProfile, pstats
    prof = cProfile.Profile()
    prof = prof.runctx("real_main()", globals(), locals())
    print '<link rel="stylesheet" href="/static/css/profile.css" type="text/css"/>'
    print "<pre id='profile'>"
    stats = pstats.Stats(prof)
    stats.sort_stats("time")  # Or cumulative
    stats.print_stats(80)  # 80 = how many to print
    # The rest is optional.
    print "----------"
    stats.print_callees()
    stats.print_callers()
    print "</pre>"

if __name__ == "__main__":
    real_main()
    #profile_main()
