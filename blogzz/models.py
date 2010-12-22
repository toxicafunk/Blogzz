from google.appengine.ext import db
  

class Content(db.Model):
    author = db.UserProperty()
    markdown = db.TextProperty(required=True)
    html = db.TextProperty(required=True)
    published = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    origin = db.StringProperty()

class Entry(Content):
    """A single blog entry."""
    title = db.StringProperty(required=True)
    slug = db.StringProperty(required=True)
    
    def __unicode__(self):
        return '%s\n%s' % (self.title,self.markdown)
    
class Comment(Content):
    """ Same as entry but with a refrence to the Entry it belongs
        to and no title or slug."""
    entry = db.ReferenceProperty(Entry) 
    
class Attachment(db.Model):
    entry = db.ReferenceProperty(Entry)
    type = db.StringProperty()
    preview = db.LinkProperty()
    enclosure = db.LinkProperty