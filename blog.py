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

import tornado.wsgi
import wsgiref.handlers

import blogzz.handlers as handlers

settings = {
    "blog_title": u"Sin Animo de Lucro",
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "ui_modules": {"Entry": handlers.EntryModule},
    "xsrf_cookies": True,
}
application = tornado.wsgi.WSGIApplication([
    (r"/", handlers.HomeHandler),
    (r"/archive", handlers.ArchiveHandler),
    (r"/feed", handlers.FeedHandler),
    (r"/entry/([^/]+)", handlers.EntryHandler),
    (r"/compose", handlers.ComposeHandler),
], **settings)


def main():
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
