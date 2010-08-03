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

import functools
import markdown
import os.path
import re
import tornado.web
import tornado.wsgi
import unicodedata
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import db

import buzz
import blogzz.models as models

token = verification_code = buzz_client = ''

def administrator(method):
    """Decorate with this method to restrict to site admins."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method == "GET":
                self.redirect(self.get_login_url())
                return
            raise tornado.web.HTTPError(403)
        elif not self.current_user.administrator:
            if self.request.method == "GET":
                self.redirect("/")
                return
            raise tornado.web.HTTPError(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper


class BaseHandler(tornado.web.RequestHandler):
    """Implements Google Accounts authentication methods."""
    def get_current_user(self):
        user = users.get_current_user()
        if user: user.administrator = users.is_current_user_admin()
        return user

    def get_login_url(self):
        return users.create_login_url(self.request.uri)

    def render_string(self, template_name, **kwargs):
        # Let the templates access the users module to generate login URLs
        return tornado.web.RequestHandler.render_string(
            self, template_name, users=users, **kwargs)


class HomeHandler(BaseHandler):
    def get(self):
        global token, verification_code, buzz_client
        
        entries = db.Query(models.Entry).order('-published').fetch(limit=5)
        if not entries:
            if not self.current_user or self.current_user.administrator:
                self.redirect("/compose")
                return
        
        # let's query buzz
        user_id = '@me'
        buzz_user = buzz_client.person(user_id).data
        buzz_posts = buzz_client.posts(user_id=user_id).data
        #buzz_posts = buzz_client.search("date:2010-07-30").data
        self.render("home.html", entries=entries, buzz_user=buzz_user, buzz_posts=buzz_posts)


class EntryHandler(BaseHandler):
    def get(self, slug):
        entry = db.Query(models.Entry).filter("slug =", slug).get()
        if not entry: raise tornado.web.HTTPError(404)
        self.render("entry.html", entry=entry)


class ArchiveHandler(BaseHandler):
    def get(self):
        entries = db.Query(models.Entry).order('-published')
        self.render("archive.html", entries=entries)


class FeedHandler(BaseHandler):
    def get(self):
        entries = db.Query(Entry).order('-published').fetch(limit=10)
        self.set_header("Content-Type", "application/atom+xml")
        self.render("feed.xml", entries=entries)


class ComposeHandler(BaseHandler):
    @administrator
    def get(self):
        key = self.get_argument("key", None)
        entry = Entry.get(key) if key else None
        self.render("compose.html", entry=entry)

    @administrator
    def post(self):
        key = self.get_argument("key", None)
        if key:
            entry = models.Entry.get(key)
            entry.title = self.get_argument("title")
            entry.markdown = self.get_argument("markdown")
            entry.html = markdown.markdown(self.get_argument("markdown"))
        else:
            title = self.get_argument("title")
            slug = unicodedata.normalize("NFKD", title).encode(
                "ascii", "ignore")
            slug = re.sub(r"[^\w]+", " ", slug)
            slug = "-".join(slug.lower().strip().split())
            if not slug: slug = "entry"
            while True:
                existing = db.Query(models.Entry).filter("slug =", slug).get()
                if not existing or str(existing.key()) == key:
                    break
                slug += "-2"
            entry = models.Entry(
                author=self.current_user,
                title=title,
                slug=slug,
                markdown=self.get_argument("markdown"),
                html=markdown.markdown(self.get_argument("markdown")),
            )
        entry.put()
        self.redirect("/entry/" + entry.slug)


class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)


settings = {
    "blog_title": u"Sin Animo de Lucro",
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "ui_modules": {"Entry": EntryModule},
    "xsrf_cookies": True,
}
application = tornado.wsgi.WSGIApplication([
    (r"/", HomeHandler),
    (r"/archive", ArchiveHandler),
    (r"/feed", FeedHandler),
    (r"/entry/([^/]+)", EntryHandler),
    (r"/compose", ComposeHandler),
], **settings)


def main():
    global token, verification_code, buzz_client
    
    buzz_client = buzz.Client()
    buzz_client.oauth_scopes=[buzz.FULL_ACCESS_SCOPE]
    buzz_client.use_anonymous_oauth_consumer()
    token = buzz_client.fetch_oauth_request_token('oob')
    
    key = "1/iw6C3IqsVvN7P_kdGx3xnW9odteT3hAccAzSecXwY6k"
    secret = "tBdemlPh21Wuei3s104mxE3z"
    
    buzz_client.build_oauth_access_token(key, secret)
    
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()
