import tornado
import logging
import re

class EntryModule(tornado.web.UIModule):
    def render(self, entry, blog, isPreview=True):
        logging.debug("BLOG: %s ENTRY: %s isPreview: %s" % (blog,entry,isPreview))
        return self.render_string("modules/entry.html", blog=blog, entry=entry, isPreview=isPreview, re=re)