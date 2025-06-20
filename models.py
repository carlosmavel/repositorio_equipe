# models.py
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLAEnum, Column, Text, ForeignKey, Date, Boolean, Integer, String, DateTime
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash # Mantendo seus imports de User

from database import db # Seu objeto db
from enums import ArticleStatus, ArticleVisibility

# --- association tables for article visibility ---
article_extra_celulas = db.Table(
    'article_extra_celulas',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('celula_id', db.Integer, db.ForeignKey('celula.id'), primary_key=True)
)

article_extra_users = db.Table(
    'article_extra_users',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Association tables for users responsible for multiple setores/células
user_extra_celulas = db.Table(
    'user_extra_celulas',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('celula_id', db.Integer, db.ForeignKey('celula.id'), primary_key=True),
)

user_extra_setores = db.Table(
    'user_extra_setores',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('setor_id', db.Integer, db.ForeignKey('setor.id'), primary_key=True),
)

# Association tables for default hierarchy per cargo
cargo_default_celulas = db.Table(
    'cargo_default_celulas',
    db.Column('cargo_id', db.Integer, db.ForeignKey('cargo.id'), primary_key=True),
    db.Column('celula_id', db.Integer, db.ForeignKey('celula.id'), primary_key=True),
)

cargo_default_setores = db.Table(
    'cargo_default_setores',
    db.Column('cargo_id', db.Integer, db.ForeignKey('cargo.id'), primary_key=True),
    db.Column('setor_id', db.Integer, db.ForeignKey('setor.id'), primary_key=True),
)

# --- Permissões / Funções ---
cargo_funcoes = db.Table(
    'cargo_funcoes',
    db.Column('cargo_id', db.Integer, db.ForeignKey('cargo.id'), primary_key=True),
    db.Column('funcao_id', db.Integer, db.ForeignKey('funcao.id'), primary_key=True),
)

user_funcoes = db.Table(
    'user_funcoes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('funcao_id', db.Integer, db.ForeignKey('funcao.id'), primary_key=True),
)

class Funcao(db.Model):
    __tablename__ = 'funcao'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100), unique=True, nullable=False)
    nome = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<Funcao {self.codigo}>"


# --- NOVOS MODELOS ORGANIZACIONAIS (FASE 1) ---

class Instituicao(db.Model):
    __tablename__ = 'instituicao'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    estabelecimentos = db.relationship('Estabelecimento', back_populates='instituicao', lazy='dynamic')

    def __repr__(self):
        return f"<Instituicao {self.nome}>"


class Estabelecimento(db.Model):
    __tablename__ = 'estabelecimento'
    
    id = db.Column(db.Integer, primary_key=True)
    instituicao_id = db.Column(db.Integer, db.ForeignKey('instituicao.id'), nullable=False)
    instituicao = db.relationship('Instituicao', back_populates='estabelecimentos')
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
    setores = db.relationship('Setor', back_populates='estabelecimento', lazy='dynamic', cascade="all, delete-orphan")
    celulas = db.relationship('Celula', back_populates='estabelecimento', lazy='dynamic', cascade="all, delete-orphan")
    usuarios = db.relationship('User', back_populates='estabelecimento', lazy='dynamic')

    def __repr__(self):
        return f"<Estabelecimento {self.codigo} - {self.nome_fantasia}>"


class Setor(db.Model):
    __tablename__ = 'setor'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)
    estabelecimento = db.relationship('Estabelecimento', back_populates='setores')

    # Relacionamentos: Um Setor pode ter vários Usuários
    usuarios = db.relationship('User', back_populates='setor', lazy='dynamic')
    celulas = db.relationship('Celula', back_populates='setor', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Setor {self.nome}>"


class Celula(db.Model):
    __tablename__ = 'celula'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)
    estabelecimento = db.relationship('Estabelecimento', back_populates='celulas')
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=False)
    setor = db.relationship('Setor', back_populates='celulas')

    usuarios = db.relationship('User', back_populates='celula', lazy='dynamic')

    def __repr__(self):
        return f"<Celula {self.nome}>"


class Funcao(db.Model):
    __tablename__ = 'funcao'
    id = db.Column(db.Integer, primary_key=True)
    nome_codigo = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Funcao {self.nome_codigo}>"


class UserFuncao(db.Model):
    __tablename__ = 'user_funcoes'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao.id'), primary_key=True)
    granted = db.Column(db.Boolean, nullable=False, default=True)

    funcao = db.relationship('Funcao')
    user = db.relationship('User', back_populates='funcoes_diferenciadas')

class Cargo(db.Model):
    __tablename__ = 'cargo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    nivel_hierarquico = db.Column(db.Integer, nullable=True) # Para lógica de hierarquia (ex: 1=Alto, 10=Baixo)
    ativo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    # Relacionamentos: Um Cargo pode ter vários Usuários
    usuarios = db.relationship('User', back_populates='cargo', lazy='dynamic')
    # Hierarquia padrão para usuários deste cargo
    default_setores = db.relationship(
        'Setor', secondary=cargo_default_setores, lazy='dynamic')
    default_celulas = db.relationship(
        'Celula', secondary=cargo_default_celulas, lazy='dynamic')
    funcoes = db.relationship(
        'Funcao', secondary=cargo_funcoes, lazy='dynamic')

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
    # Um usuário pertence a um estabelecimento, um setor e tem um cargo.
    # Nullable=True para flexibilidade inicial ou para usuários que não se encaixam perfeitamente.
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=False)
    estabelecimento = db.relationship('Estabelecimento', back_populates='usuarios')

    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=False)
    setor = db.relationship('Setor', back_populates='usuarios')

    celula_id = db.Column(db.Integer, db.ForeignKey('celula.id'), nullable=False)
    celula = db.relationship('Celula', back_populates='usuarios')

    cargo_id = db.Column(db.Integer, db.ForeignKey('cargo.id'), nullable=True)
    cargo = db.relationship('Cargo', back_populates='usuarios')

    # Relações de múltiplas células e setores
    extra_celulas = db.relationship(
        'Celula', secondary=user_extra_celulas, lazy='dynamic')
    extra_setores = db.relationship(
        'Setor', secondary=user_extra_setores, lazy='dynamic')
    funcoes_diferenciadas = db.relationship(
        'UserFuncao', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')

    
    # Relacionamentos existentes (verifique se os back_populates/backrefs estão corretos com seus outros modelos)
    articles = db.relationship('Article', back_populates='author', lazy='dynamic', cascade='all, delete-orphan')
    revision_requests = db.relationship('RevisionRequest', foreign_keys='RevisionRequest.user_id', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', foreign_keys='Comment.user_id', back_populates='autor', lazy='dynamic', cascade='all, delete-orphan')




    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_permissoes(self):
        permissoes = set()
        if self.cargo:
            permissoes.update(f.nome_codigo for f in self.cargo.funcoes)
        for uf in self.funcoes_diferenciadas:
            if uf.granted:
                permissoes.add(uf.funcao.nome_codigo)
            else:
                permissoes.discard(uf.funcao.nome_codigo)
        return permissoes


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
            name="article_status",
            create_type=False
        ),
        nullable=False,
        server_default=ArticleStatus.RASCUNHO.value
    )
    visibility = db.Column(
        SQLAEnum(
            ArticleVisibility,
            values_callable=lambda x: [e.value for e in x],
            name="article_visibility",
            create_type=False
        ),
        nullable=False,
        server_default=ArticleVisibility.CELULA.value
    )
    instituicao_id = db.Column(db.Integer, db.ForeignKey('instituicao.id'), nullable=True)
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimento.id'), nullable=True)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=True)
    vis_celula_id = db.Column(db.Integer, db.ForeignKey('celula.id'), nullable=True)
    celula_id = db.Column(
        db.Integer,
        db.ForeignKey('celula.id'),
        nullable=False,
        server_default='1'
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    arquivos = db.Column(db.Text, nullable=True)  # JSON list of filenames (se for o caso, ou remover se Attachment substitui)
    review_comment = db.Column(db.Text, nullable=True) # Comentário da última revisão do editor
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', back_populates='articles')

    instituicao = db.relationship('Instituicao', foreign_keys=[instituicao_id])
    estabelecimento = db.relationship('Estabelecimento', foreign_keys=[estabelecimento_id])
    setor = db.relationship('Setor', foreign_keys=[setor_id])
    vis_celula = db.relationship('Celula', foreign_keys=[vis_celula_id])
    celula = db.relationship('Celula', foreign_keys=[celula_id])

    extra_celulas = db.relationship('Celula', secondary=article_extra_celulas, lazy='dynamic')
    extra_users = db.relationship('User', secondary=article_extra_users, lazy='dynamic')
    
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
