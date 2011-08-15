import functools
import re
import unicodedata
import datetime
import logging

try:
  import oauth.oauth as oauth
except (ImportError):
  import oauth
  
import tornado.web

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import memcache

import blogzz.buzz as buzz
import blogzz.markdown as markdown
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
		logged_user = users.get_current_user()
		if not logged_user:
			return None
		
		buzz_client_key = str(logged_user)+"_bc"
		buzz_client = memcache.get(buzz_client_key)
		
		if buzz_client is not None:
			return buzz_client
		else:
			buzz_client = buzz.Client()
			buzz_client.oauth_scopes=[buzz.FULL_ACCESS_SCOPE]
			buzz_client.use_anonymous_oauth_consumer()
			if len(self.request.path) > 1:
				buzz_key = None
				buzz_secret = None
				blog_path = self.request.path.lstrip('/')
				logging.debug("PATH: %s" % blog_path)
				current_blog = db.Query(models.Blog).filter("path =", blog_path).get()
				if current_blog:
					buzz_key = current_blog.buzz_key
					buzz_secret = current_blog.buzz_secret
					
				if buzz_key and buzz_secret:
					buzz_client.build_oauth_access_token(current_blog.buzz_key, current_blog.buzz_secret)
					# Add a value if it doesn't exist in the cache, with a cache expiration of 1 hour.
					buzz_client_key = str(current_blog.author)+"_bc"
					logging.debug("buzz_client_key: %s" % buzz_client_key)
					if not memcache.set(key=buzz_client_key, value=buzz_client, time=1800):
						logging.error("Error adding %s to memcache" % buzz_client_key)
				else:
					logging.error('No buzz key or secret found!')
			else:
				if memcache.add(key='tmp_'+buzz_client_key, value=buzz_client, time=1800):
					logging.error("Error adding %s to memcache" % 'tmp'+buzz_client_key)
			
			return buzz_client

class DashboardHandler(BaseHandler):
	def get(self):
		buzz_url = ''
		token = ''
		may_create_blog = False
		current_user_blog = None
		blogs = db.Query(models.Blog).fetch(10)
		current_user = users.get_current_user()
		logging.debug("current_user: %s" % current_user)
		if current_user:
		   current_user_blog = db.Query(models.Blog).filter("author =", current_user).get()
		
		logging.debug(blogs)
		
		if current_user and not current_user_blog:
			may_create_blog = True
			buzz_client = self.get_buzz_client()
			if buzz_client:
				token = buzz_client.fetch_oauth_request_token ('oob')
				token = buzz_client.oauth_request_token
				
				buzz_token_key = str(current_user)+'_token'
				if memcache.add(key=buzz_token_key, value=token, time=600):
					logging.error("Error adding %s to memcache" % buzz_token_key)
				buzz_url = buzz_client.build_oauth_authorization_url(token)
			
		self.render("dashboard.html", blogs=blogs, current_user_blog=current_user_blog,
					may_create_blog=may_create_blog, buzz_url=buzz_url)
	
	def post(self):
		title = self.get_argument("title", None)
		path = self.get_argument("path", None)
		verification_code = self.get_argument("code", None)
		
		buzz_token = memcache.get(str(users.get_current_user())+'_token')
		if buzz_token is None:
			logging.error("No buzz_token!")
			#return ERROR
		
		buzz_client = self.get_buzz_client()
		logging.debug("Authorizing token: %s" % buzz_token)
		buzz_client.fetch_oauth_access_token(verification_code, buzz_token)
		
		blog = models.Blog(
			title = title,
			author = users.get_current_user(),
			path = path,
			buzz_key = buzz_client.oauth_access_token.key,
			buzz_secret = buzz_client.oauth_access_token.secret
		)
		blog.put()
		self.redirect("/"+path)
		return

class HomeHandler(BaseHandler):
	def get(self, blog_path):
		global last_buzz
		blog = db.Query(models.Blog).filter("path =", blog_path).get()
		if self.settings["use_buzz"] and (not last_buzz or (datetime.datetime.now() - last_buzz).seconds > 120):
			# let's query buzz
			# Need to change so that it logins user
			buzz_client = self.get_buzz_client()
			try:
				buzz_posts = buzz_client.posts(user_id=str("@me"), type_id='@self').data
			except Exception, e:
				logging.error(e)
			#buzz_posts = buzz_client.search("date:2010-07-30").data
			#import pdb; pdb.set_trace()
			last_buzz = datetime.datetime.now()
			logging.debug("obtained %d buzzes" % len(buzz_posts))
			importer.import_buzzes(blog, buzz_posts,self.current_user)

		entries = db.Query(models.Entry).filter("blog =", blog).order('-published').fetch(limit=10)
		if not entries:
			if not self.current_user or self.current_user.administrator:
				self.redirect("/compose")
				return
		
		#I don't like this but can't think of another solution
		'''for entry in entries:
			logging.debug(entry.attachment_set.fetch(5))'''

		self.render("home.html", entries=entries, blog=blog)

class AtomTestHandler(BaseHandler):
	def get(self):
		global last_buzz        
		# let's query buzz
		buzz_client = self.get_buzz_client()
		if authorizedforbuzz:
			user_id = 'laguatusa504'
			buzz_posts = buzz_client.postsatom(type_id="@public",user_id=user_id).data
			logging.info("obtained %d buzzes" % len(buzz_posts))
			self.render("atom.html", entries=buzz_posts)
		else:
			self.render("atom.html", entries=["Not authorized for buzz"])
		
class SubHubHandler(BaseHandler):
	def get(self):
		global last_buzz        
		# let's query buzz
		buzz_client,authorizedforbuzz = self.get_buzz_client()
		if authorizedforbuzz:
			user_id = 'laguatusa504'
			resp = buzz_client.subscribe2hub(type_id="@public",user_id=user_id)
			self.render("atom.html", entries=resp.read())
		else:
			self.render("atom.html", entries=["Not authorized for buzz"])
	
class HubCallbackHandler(BaseHandler):
	def post(self):
		challenge = self.get_argument('hub.challenge')
		self.set_status('200')
		logging.debug('Callback received:' + self.request)
		self.write(challenge)

class EntryHandler(BaseHandler):
	def get(self, blog_path, slug, isPreview=False):
		blog = db.Query(models.Blog).filter("path =", blog_path).get()
		entry = db.Query(models.Entry).filter("blog =", blog).filter("slug =", slug).get()
		'''youtube_links = None
		if entry.type == 'video':
			youtube_links = re.compile('http://.*\.youtube\.com/.*autoshare').findall(entry.html)'''
		if not entry: raise tornado.web.HTTPError(404)
		self.render("entry.html", entry=entry, blog=blog, isPreview=isPreview)


class ArchiveHandler(BaseHandler):
	def get(self,blog_path):
		blog = db.Query(models.Blog).filter("path =", blog_path).get()
		entries = blog.entry_set.order('-published').get()
		#entries = db.Query(models.Entry).filter("blog =", blog).order('-published').fetch(limit=100)
		if not entries: raise tornado.web.HTTPError(404)
		self.render("archive.html", entries=entries, blog=blog)


class FeedHandler(BaseHandler):
	def get(self):
		entries = db.Query(models.Entry).order('-published').fetch(limit=10)
		self.set_header("Content-Type", "application/atom+xml")
		self.render("feed.xml", entries=entries)


class ComposeHandler(BaseHandler):
	@administrator
	def get(self):
		logging.debug("Entro a compose")
		key = self.get_argument("key", None)
		entry = models.Entry.get(key) if key else None
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
