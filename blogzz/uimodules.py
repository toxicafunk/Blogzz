import tornado

class EntryModule(tornado.web.UIModule):
    def render(self, entry, isPreview=True):
        return self.render_string("modules/entry.html", entry=entry, isPreview=isPreview)