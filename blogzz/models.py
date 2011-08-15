from google.appengine.ext import db

class Blog(db.Model):
	title = db.StringProperty()
	author = db.UserProperty(required=True)
	path = db.StringProperty()
	buzz_key = db.StringProperty()
	buzz_secret = db.StringProperty()
	
	def __repr__(self):
		return self.title

class Content(db.Model):
	markdown = db.TextProperty(required=True)
	html = db.TextProperty(required=True)
	published = db.DateTimeProperty(auto_now_add=True)
	updated = db.DateTimeProperty(auto_now=True)
	origin = db.StringProperty()

class Entry(Content):
	"""A single blog entry."""
	title = db.StringProperty(required=True)
	slug = db.StringProperty(required=True)
	blog = db.ReferenceProperty(Blog)
	type = db.StringProperty()
	
	def __repr__(self):
		return '%s' % (self.title)
	
class Comment(Content):
	""" Same as entry but with a refrence to the Entry it belongs
		to and no title or slug."""
	entry = db.ReferenceProperty(Entry) 
	
class Attachment(db.Model):
	entry = db.ReferenceProperty(Entry)
	type = db.StringProperty()
	preview = db.LinkProperty()
	enclosure = db.LinkProperty()
	
	def __repr__(self):
		return '%s\n%s' % (self.preview,self.enclosure)