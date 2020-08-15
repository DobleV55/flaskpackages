
from flask_security import (
    UserMixin,
    RoleMixin
)
from flask_packages.web import app, db
from flask_security import Security, MongoEngineUserDatastore


class Role(db.Document, RoleMixin):
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)


class user(db.Document, UserMixin):
    email = db.StringField(max_length=255)
    password = db.StringField(max_length=255)
    active = db.BooleanField(default=True)
    fs_uniquifier = db.StringField(max_length=255)
    confirmed_at = db.DateTimeField()
    roles = db.ListField(db.ReferenceField(Role), default=[])


class Version(db.Document):
    version = db.StringField()
    date = db.DateTimeField()
    link = db.StringField()
    sha256 = db.StringField()


class Classifier(db.Document):
    development_status = db.ListField(db.StringField())
    programming_language = db.ListField(db.StringField())
    topic = db.ListField(db.StringField())


class GithubStats(db.Document):
    stars = db.IntField()
    open_pr = db.IntField()
    forks = db.IntField()


class Project(db.Document):
    name = db.StringField(unique=True)
    description = db.StringField()
    lastest_version = db.StringField()
    maintainer = db.StringField()
    homepage = db.StringField()
    pypi_link = db.StringField(unique=True)

    versions = db.ListField(db.EmbeddedDocumentField(Version))
    github_stats = db.EmbeddedDocumentField(GithubStats)
    tags = db.ListField(db.StringField())
    classifiers = db.ListField(db.EmbeddedDocumentField(Classifier))

    release = db.DateTimeField()
    #category = db.ListField(db.Strin


# Setup Flask-Security
user_datastore = MongoEngineUserDatastore(db, user, Role)
security = Security(app, user_datastore)