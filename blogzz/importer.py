import logging,unicodedata,re,datetime
import markdown

from google.appengine.ext import db

import blogzz.models as models

def import_buzzes(posts,user):
    """Eventually this has to evolve into a Class intead of a method"""
    for post in posts:
        title = post.title
        slug = unicodedata.normalize("NFKD", title).encode(
            "ascii", "ignore")
        slug = re.sub(r"[^\w]+", " ", slug)
        slug = "-".join(slug.lower().strip().split())
        #name = "/".join(slug.lower().strip().split())
        if not slug: slug = "entry"
        existing = db.Query(models.Entry).filter("slug =", slug).get()
        if not existing:
            dp,_,_ = post.published.partition('.')
            #du,_,_ = post.updated.partition('.')
            entry = models.Entry(
                key_name= "k/"+slug, #maybe we don't need a key_name since slug takes care of uniqueness
                origin = "buzz",
                author=user,
                title=title,
                slug=slug,
                markdown=post.content,
                html=markdown.markdown(post.content),
                
                published=datetime.datetime.strptime(dp,"%Y-%m-%dT%H:%M:%S")
                #updated=datetime.datetime.strptime(du,"%Y-%m-%dT%H:%M:%S")
            )
            entry.put()
            logging.debug(entry)
            