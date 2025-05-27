from sqlalchemy.sql import func
from database import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum as SQLAEnum, Column, Text, ForeignKey
from sqlalchemy.orm import relationship
from enums import ArticleStatus

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nome_completo = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    foto = db.Column(db.String(255), nullable=True)

    # Relacionamentos
    articles = db.relationship(
        'Article',
        back_populates='author',
        lazy=True,
        cascade='all, delete-orphan'
    )
    revision_requests = db.relationship(
        'RevisionRequest',
        back_populates='user',
        lazy=True,
        cascade='all, delete-orphan'
    )
    notifications = db.relationship(
        'Notification',
        back_populates='user',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Article(db.Model):
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    status = db.Column(
        SQLAEnum(
            ArticleStatus,
            values_callable=lambda x: [e.value for e in x],
            name="article_status",
            native_enum=False
        ),
        nullable=False,
        server_default="rascunho"
    )

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    arquivos = db.Column(db.Text, nullable=True)  # JSON list of filenames
    review_comment = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    author = db.relationship('User', back_populates='articles')
    revision_requests = db.relationship(
        'RevisionRequest',
        back_populates='article',
        lazy=True,
        cascade='all, delete-orphan'
    )

    # Novo relacionamento para attachments
    attachments = db.relationship(
        'Attachment',
        back_populates='article',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Article {self.titulo}>"

class RevisionRequest(db.Model):
    __tablename__ = 'revision_request'
    id = db.Column(db.Integer, primary_key=True)
    artigo_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comentario = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    article = db.relationship('Article', back_populates='revision_requests')
    user = db.relationship('User', back_populates='revision_requests')

    def __repr__(self):
        return f"<RevisionRequest artigo={self.artigo_id} user={self.user_id}>"
    
class Comment(db.Model):
    __tablename__ = "comment"
    id          = db.Column(db.Integer, primary_key=True)
    artigo_id   = db.Column(db.Integer, db.ForeignKey("article.id"), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    texto       = db.Column(db.Text,    nullable=False)
    created_at  = db.Column(db.DateTime(timezone=True), server_default=func.now())

    autor  = db.relationship("User", backref="comments")
    artigo = db.relationship("Article", backref="comments")  

class Attachment(db.Model):
    __tablename__ = 'attachment'
    id = Column(db.Integer, primary_key=True)
    article_id = Column(db.Integer, ForeignKey('article.id', ondelete='CASCADE'), nullable=False)
    filename = Column(Text, nullable=False)
    mime_type = Column(Text, nullable=False)
    content = Column(Text, nullable=True)  # texto extraído
    created_at = Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relacionamento de volta para o artigo
    article = relationship('Article', back_populates='attachments')

class Notification(db.Model):
    __tablename__ = 'notification'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message    = db.Column(db.String(255), nullable=False)
    url        = db.Column(db.String(255), nullable=False)
    lido       = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = db.relationship('User', back_populates='notifications')
    
    def __repr__(self):
        return f"<Notification to={self.user_id} message={self.message}>"