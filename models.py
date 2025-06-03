# models.py
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLAEnum, Column, Text, ForeignKey, Date, Boolean, Integer, String, DateTime
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash # Mantendo seus imports de User

from database import db # Seu objeto db
from enums import ArticleStatus # Seu enum de ArticleStatus

# --- NOVOS MODELOS ORGANIZACIONAIS (FASE 1) ---

class Estabelecimento(db.Model):
    __tablename__ = 'estabelecimento'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False) # Código interno ou identificador
    nome_fantasia = db.Column(db.String(200), nullable=False)     # Nome popular do estabelecimento
    
    # --- Novos Campos de Detalhes e Endereço ---
    razao_social = db.Column(db.String(255), nullable=True)     # Nome legal/oficial
    cnpj = db.Column(db.String(18), unique=True, nullable=True) # Formato XX.XXX.XXX/XXXX-XX
    inscricao_estadual = db.Column(db.String(20), nullable=True)
    inscricao_municipal = db.Column(db.String(20), nullable=True)
    
    tipo_estabelecimento = db.Column(db.String(50), nullable=True) # Ex: "Matriz", "Filial", "Depósito", "Loja"
    
    # Endereço
    cep = db.Column(db.String(9), nullable=True)                 # Formato XXXXX-XXX
    logradouro = db.Column(db.String(255), nullable=True)        # Rua, Avenida, Praça, etc.
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)       # Sala, Bloco, Apto
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)              # Sigla UF, ex: SP, MG
    pais = db.Column(db.String(50), nullable=True, default='Brasil') # Se aplicável

    # Contato
    telefone_principal = db.Column(db.String(20), nullable=True)
    telefone_secundario = db.Column(db.String(20), nullable=True)
    email_contato = db.Column(db.String(120), nullable=True)     # Email geral do estabelecimento

    # Outras Informações
    data_abertura = db.Column(db.Date, nullable=True)            # Data de fundação/início
    observacoes = db.Column(db.Text, nullable=True)              # Campo para notas diversas

    # Status Ativo/Inativo (como discutimos)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    
    # Timestamps (opcional, mas útil)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relacionamentos (como já tínhamos) ---
    centros_custo = db.relationship('CentroDeCusto', back_populates='estabelecimento', lazy='dynamic', cascade="all, delete-orphan")
    usuarios = db.relationship('User', back_populates='estabelecimento', lazy='dynamic')

    def __repr__(self):
        return f"<Estabelecimento {self.codigo} - {self.nome_fantasia}>"

class CentroDeCusto(db.Model):
    __tablename__ = 'centro_custo'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)
    estabelecimento = db.relationship('Estabelecimento', back_populates='centros_custo')

    # Relacionamentos: Um CentroDeCusto pode ter vários Setores e vários Usuários
    setores = db.relationship('Setor', back_populates='centro_custo', lazy='dynamic', cascade="all, delete-orphan")
    usuarios = db.relationship('User', back_populates='centro_custo', lazy='dynamic')

    def __repr__(self):
        return f"<CentroDeCusto {self.codigo} - {self.nome}>"

class Setor(db.Model):
    __tablename__ = 'setor'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    
    centro_custo_id = db.Column(db.Integer, db.ForeignKey('centro_custo.id'), nullable=True) # Setor PODE pertencer a um CC
    centro_custo = db.relationship('CentroDeCusto', back_populates='setores')

    # Relacionamentos: Um Setor pode ter vários Usuários
    usuarios = db.relationship('User', back_populates='setor', lazy='dynamic')

    def __repr__(self):
        return f"<Setor {self.nome}>"

class Cargo(db.Model):
    __tablename__ = 'cargo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    nivel_hierarquico = db.Column(db.Integer, nullable=True) # Para lógica de hierarquia (ex: 1=Alto, 10=Baixo)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    # Relacionamentos: Um Cargo pode ter vários Usuários
    usuarios = db.relationship('User', back_populates='cargo', lazy='dynamic')

    def __repr__(self):
        return f"<Cargo {self.nome}>"

# --- MODELO USER ATUALIZADO ---

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) # Campo importante
    password_hash = db.Column(db.String(256), nullable=False)
    nome_completo = db.Column(db.String(255), nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(50), nullable=False, default='colaborador') # Campo role existente

    # Novos campos para cadastro completo
    matricula = db.Column(db.String(50), unique=True, nullable=True)
    cpf = db.Column(db.String(14), unique=True, nullable=True) 
    rg = db.Column(db.String(20), nullable=True)
    ramal = db.Column(db.String(20), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    data_admissao = db.Column(db.Date, nullable=True)
    telefone_contato = db.Column(db.String(20), nullable=True) # Pode ser o celular ou outro contato
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    # Novas Chaves Estrangeiras e Relacionamentos (Fase 1)
    # Um usuário pertence a um estabelecimento, um CC, um setor e tem um cargo.
    # Nullable=True para flexibilidade inicial ou para usuários que não se encaixam perfeitamente.
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=True)
    estabelecimento = db.relationship('Estabelecimento', back_populates='usuarios')

    centro_custo_id = db.Column(db.Integer, db.ForeignKey('centro_custo.id'), nullable=True)
    centro_custo = db.relationship('CentroDeCusto', back_populates='usuarios')

    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=True)
    setor = db.relationship('Setor', back_populates='usuarios')

    cargo_id = db.Column(db.Integer, db.ForeignKey('cargo.id'), nullable=True)
    cargo = db.relationship('Cargo', back_populates='usuarios')
    
    # Relacionamentos existentes (verifique se os back_populates/backrefs estão corretos com seus outros modelos)
    articles = db.relationship('Article', back_populates='author', lazy='dynamic', cascade='all, delete-orphan')
    revision_requests = db.relationship('RevisionRequest', foreign_keys='RevisionRequest.user_id', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', foreign_keys='Comment.user_id', back_populates='autor', lazy='dynamic', cascade='all, delete-orphan')

    # Perfil (Fase 2) - Descomentar quando formos para a Fase 2
    # perfil_id = db.Column(db.Integer, db.ForeignKey('perfil.id'), nullable=True)
    # perfil = db.relationship('Perfil', backref=db.backref('users', lazy='dynamic'))


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

# --- SEUS MODELOS EXISTENTES (Article, RevisionRequest, Notification, Comment, Attachment) ---
# Cole eles aqui, ajustando os relacionamentos com User se necessário (ex: usando back_populates)

class Article(db.Model):
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    status = db.Column(
        SQLAEnum(
            ArticleStatus,
            values_callable=lambda x: [e.value for e in x],
            name="article_status", # Nome do tipo ENUM no banco, pode precisar ser 'article_status' se já existe
            create_type=False # Se o tipo ENUM já foi criado por uma migration raw SQL
        ), 
        nullable=False, 
        server_default=ArticleStatus.RASCUNHO.value
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    arquivos = db.Column(db.Text, nullable=True)  # JSON list of filenames (se for o caso, ou remover se Attachment substitui)
    review_comment = db.Column(db.Text, nullable=True) # Comentário da última revisão do editor
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', back_populates='articles') # author é o User
    
    revision_requests = db.relationship('RevisionRequest', back_populates='article', lazy='dynamic', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', back_populates='article', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='artigo', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Article {self.titulo}>"

class RevisionRequest(db.Model):
    __tablename__ = 'revision_request'
    id = db.Column(db.Integer, primary_key=True)
    artigo_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Usuário que solicitou a revisão
    comentario = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=True) # Conforme migration

    article = db.relationship('Article', back_populates='revision_requests')
    user = db.relationship('User', foreign_keys=[user_id], back_populates='revision_requests') # Usuário solicitante

    def __repr__(self):
        return f"<RevisionRequest artigo={self.artigo_id} user={self.user_id}>"

class Comment(db.Model):
    __tablename__ = "comment" # Comentários feitos por editores/admins durante o fluxo de aprovação
    id = db.Column(db.Integer, primary_key=True)
    artigo_id = db.Column(db.Integer, db.ForeignKey("article.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False) # Editor/Admin que comentou
    texto = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=True) # Conforme migration

    autor = db.relationship("User", foreign_keys=[user_id], back_populates="comments") # Editor/Admin
    artigo = db.relationship("Article", back_populates="comments")

    def __repr__(self):
        return f"<Comment id={self.id} by user_id={self.user_id} on article_id={self.artigo_id}>"

class Attachment(db.Model):
    __tablename__ = 'attachment'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.Text, nullable=False) # Nome único salvo no disco
    original_filename = db.Column(db.Text, nullable=True) # Nome original do arquivo
    mime_type = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=True)  # texto extraído para busca
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    article = db.relationship('Article', back_populates='attachments')

    def __repr__(self):
        return f"<Attachment {self.filename} for article_id={self.article_id}>"

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Para quem é a notificação
    message = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False) # nullable=False conforme última migration
    lido = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = db.relationship('User', back_populates='notifications')
    
    def __repr__(self):
        return f"<Notification to_user_id={self.user_id} message='{self.message[:30]}...'>"

# --- FIM DOS MODELOS ---