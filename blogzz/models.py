from google.appengine.ext import db

class Content(db.Model):
    author = db.UserProperty()
    markdown = db.TextProperty(required=True)
    html = db.TextProperty(required=True)
    published = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

class Entry(Content):
    """A single blog entry."""
    title = db.StringProperty(required=True)
    slug = db.StringProperty(required=True)
    
class Comment(Content):
    """ Same as entry but with a refrence to the Entry it belongs
        to and no title or slug."""
    entry = db.ReferenceProperty(Entry)

class Buzz(Content):
    """ Besides all properties in Content, a Buzz instance also
        has the complete json returned from google buzz."""
    json = db.TextProperty(required=True)
    

