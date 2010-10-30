import functools
import markdown
import re
import tornado.web
import unicodedata
import datetime
import logging

from google.appengine.api import users
from google.appengine.ext import db

import buzz
import blogzz.models as models
import blogzz.importer as importer

last_buzz = None

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
    def __init__(self, application, request):
        tornado.web.RequestHandler.__init__(self,application,request)
        self.buzz_client = None
        
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
    
    def get_buzz_client(self):
        if not self.buzz_client:
            self.buzz_client = buzz.Client()
            self.buzz_client.oauth_scopes=[buzz.FULL_ACCESS_SCOPE]
            self.buzz_client.use_anonymous_oauth_consumer()
            # creo que no se necesita token
            token = self.buzz_client.fetch_oauth_request_token('oob')
            
            key = "1/iw6C3IqsVvN7P_kdGx3xnW9odteT3hAccAzSecXwY6k"
            secret = "tBdemlPh21Wuei3s104mxE3z"
            
            self.buzz_client.build_oauth_access_token(key, secret)
        
        return self.buzz_client

class HomeHandler(BaseHandler):
    def get(self):
        global last_buzz
        
        if self.settings["use_buzz"] and (not last_buzz or (datetime.datetime.now() - last_buzz).seconds > 120):
            # let's query buzz
            buzz_client = self.get_buzz_client()
            user_id = '@me'
            buzz_posts = buzz_client.posts(user_id=user_id).data
            #buzz_posts = buzz_client.search("date:2010-07-30").data
            last_buzz = datetime.datetime.now()
            logging.info("obtained %d buzzes" % len(buzz_posts))
            importer.import_buzzes(buzz_posts,self.current_user)
        
        entries = db.Query(models.Entry).order('-published').fetch(limit=5)
        if not entries:
            if not self.current_user or self.current_user.administrator:
                self.redirect("/compose")
                return
            
        self.render("home.html", entries=entries)


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
            #name = "/".join(slug.lower().strip().split())
            if not slug: slug = "entry"
            while True:
                existing = db.Query(models.Entry).filter("slug =", slug).get()
                if not existing or str(existing.key()) == key:
                    break
                slug += "-2"
            entry = models.Entry(
                key_name= "k/"+slug,
                origin = "blogzz",
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

