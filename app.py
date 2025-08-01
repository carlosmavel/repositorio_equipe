# app.py

# -------------------------------------------------------------------------
# IMPORTS (Mantendo os seus e garantindo os necessários)
# -------------------------------------------------------------------------
import os
import json
import time
import uuid
import re # Você já tinha, bom para futuras validações
from datetime import datetime, timezone # Adicionei datetime aqui se for usar em 'strptime' na rota de perfil
from zoneinfo import ZoneInfo # Você já tinha

from flask import (
    Flask, request, render_template, redirect, url_for,
    session, send_from_directory, flash, jsonify # Adicionei jsonify se for usar em APIs futuras
)
import logging
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash # generate_password_hash se for resetar senha no admin
from sqlalchemy import or_, func
#from models import user_funcoes

try:
    from .database import db
except ImportError:  # pragma: no cover - fallback for direct execution
    from database import db
try:
    from .enums import ArticleStatus, ArticleVisibility, Permissao
except ImportError:  # pragma: no cover - fallback for direct execution
    from enums import ArticleStatus, ArticleVisibility, Permissao

try:
    from .models import (
        User,
        Article,
        RevisionRequest,
        Notification,
        Comment,
        Attachment,
        Instituicao,
        Celula,
        Estabelecimento,
        Setor,
        Cargo,
        Instituicao,
        Funcao,
        user_funcoes,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from models import (
        User,
        Article,
        RevisionRequest,
        Notification,
        Comment,
        Attachment,
        Instituicao,
        Celula,
        Estabelecimento,
        Setor,
        Cargo,
        Instituicao,
        Funcao,
        user_funcoes,
    )

try:
    from .utils import (
        sanitize_html,
        extract_text,
        DEFAULT_NEW_USER_PASSWORD,
        generate_random_password,
        generate_token,
        confirm_token,
        send_email,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
        eligible_review_notification_users,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (
        sanitize_html,
        extract_text,
        DEFAULT_NEW_USER_PASSWORD,
        generate_random_password,
        generate_token,
        confirm_token,
        send_email,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
        eligible_review_notification_users,
    )
from mimetypes import guess_type # Se for usar, descomente
from werkzeug.utils import secure_filename # Útil para uploads, como na sua foto de perfil

# -------------------------------------------------------------------------
# Constantes de apoio
# -------------------------------------------------------------------------
# Mapeamento dos níveis hierárquicos de cargos. A chave numérica é armazenada no
# banco de dados, enquanto o valor textual é apresentado nas interfaces.
NIVEIS_HIERARQUICOS = [
    (1, 'Diretor'),
    (2, 'Gerente'),
    (3, 'Coordenador'),
    (4, 'Supervisor'),
    (5, 'Líder'),
    (6, 'Analista Sênior'),
    (7, 'Analista Pleno'),
    (8, 'Analista Júnior'),
    (9, 'Assistente I'),
    (10, 'Assistente II'),
]
NOME_NIVEL_CARGO = {valor: nome for valor, nome in NIVEIS_HIERARQUICOS}

# -------------------------------------------------------------------------
# Configuração da Aplicação (Seu código existente)
# -------------------------------------------------------------------------
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# SECRET_KEY - Agora obrigatória via variável de ambiente
SECRET_KEY_FROM_ENV = os.environ.get('SECRET_KEY')
if not SECRET_KEY_FROM_ENV or SECRET_KEY_FROM_ENV == 'chave_de_desenvolvimento_muito_segura_trocar_em_prod':
    # Você pode ser ainda mais estrito e só checar "if not SECRET_KEY_FROM_ENV:"
    # se quiser que QUALQUER valor no fallback do código seja um erro.
    raise ValueError("ERRO CRÍTICO: SECRET_KEY não está definida corretamente no ambiente ou está usando o valor padrão inseguro!")
app.secret_key = SECRET_KEY_FROM_ENV
app.logger.info(
    "SECRET_KEY carregada do ambiente: %s...%s",
    app.secret_key[:5],
    app.secret_key[-5:],
)

# DATABASE_URI - Agora obrigatória via variável de ambiente
DATABASE_URI_FROM_ENV = os.environ.get('DATABASE_URI')
if not DATABASE_URI_FROM_ENV:
    # Se você quer que o fallback NUNCA seja usado e sempre exija a variável de ambiente:
    raise ValueError("ERRO CRÍTICO: DATABASE_URI não está definida nas variáveis de ambiente!")
# Se você ainda quisesse manter o fallback como uma opção, mas ser avisado (como no passo 1):
# elif DATABASE_URI_FROM_ENV == 'postgresql://appuser:AppUser2025%21@localhost:5432/repositorio_equipe_db':
# print("AVISO: DATABASE_URI está usando o valor padrão do código. Considere definir no ambiente.")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI_FROM_ENV

# Para não expor a senha no print, vamos mostrar uma versão modificada
uri_parts_test = app.config['SQLALCHEMY_DATABASE_URI'].split('@')
if len(uri_parts_test) == 2:
    creds_part_test = uri_parts_test[0].split(':')
    user_part_test = creds_part_test[0].split('//')[-1]
    printed_uri_test = f"postgresql://{user_part_test}:[SENHA_OCULTA]@{uri_parts_test[1]}"
    app.logger.info("DATABASE_URI carregada do ambiente: %s", printed_uri_test)
else:
    app.logger.info(
        "DATABASE_URI carregada do ambiente: %s",
        app.config['SQLALCHEMY_DATABASE_URI'],
    )

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

try:
    from .blueprints.admin import admin_bp
    from .blueprints.auth import auth_bp
    from .blueprints.articles import articles_bp
    from .blueprints.processos import processos_bp
except ImportError:  # pragma: no cover - fallback for direct execution
    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp
    from blueprints.articles import articles_bp
    from blueprints.processos import processos_bp


app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(articles_bp)
app.register_blueprint(processos_bp)

for rule in list(app.url_map.iter_rules()):
    if rule.endpoint.startswith('admin_bp.') or rule.endpoint.startswith('auth_bp.') or rule.endpoint.startswith('articles_bp.') or rule.endpoint.startswith('processos_bp.'):
        app.add_url_rule(
            rule.rule,
            endpoint=rule.endpoint.split('.',1)[-1],
            view_func=app.view_functions[rule.endpoint],
            methods=rule.methods,
        )

# Pastas de upload (Seu código existente)
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads') # Melhor usar app.root_path para caminhos
PROFILE_PICS_FOLDER = os.path.join(app.root_path, 'static', 'profile_pics')
for folder in (UPLOAD_FOLDER, PROFILE_PICS_FOLDER):
    os.makedirs(folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER

def password_meets_requirements(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def send_password_email(user: User, action: str) -> None:
    token = generate_token(user.id, action)
    if action == 'reset':
        url = url_for('reset_password_token', token=token, _external=True)
        action_text = 'redefinir'
    else:
        url = url_for('set_password_token', token=token, _external=True)
        action_text = 'criar'
    html = render_template('email/password_email.html', user=user, url=url, action=action_text)
    send_email(user.email, 'Definição de Senha', html)

# -------------------------------------------------------------------------
# NOTIFICAÇÕES - API
# -------------------------------------------------------------------------
@app.route('/api/notifications')
def api_notifications():
    """Retorna notificações paginadas para o usuário atual."""
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))
    notifs = (
        Notification.query
        .filter_by(user_id=session['user_id'], lido=False, tipo='geral')
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify([
        {'id': n.id, 'message': n.message, 'url': n.url}
        for n in notifs
    ])


@app.route('/api/os_notifications')
def api_os_notifications():
    """Retorna notificações de ordem de serviço paginadas."""
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))
    notifs = (
        Notification.query
        .filter_by(user_id=session['user_id'], lido=False, tipo='os')
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify([
        {'id': n.id, 'message': n.message, 'url': n.url}
        for n in notifs
    ])


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def api_notification_mark_read(notif_id):
    """Marca uma notificação específica como lida."""
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    notif = Notification.query.filter_by(id=notif_id, user_id=session['user_id']).first()
    if not notif:
        return jsonify({'error': 'not found'}), 404
    if not notif.lido:
        notif.lido = True
        db.session.commit()
    return jsonify({'success': True})

# -------------------------------------------------------------------------
# DECORADORES
# -------------------------------------------------------------------------
try:
    from .decorators import admin_required
except ImportError:  # pragma: no cover
    from decorators import admin_required

# -------------------------------------------------------------------------
# Context Processors
# -------------------------------------------------------------------------
@app.context_processor
def inject_notificacoes():
    if 'user_id' in session: # Usar user_id é mais seguro que username para buscar no banco
        user = User.query.get(session['user_id']) # Usar .get() é mais direto para PK
        if user:
            q_general = Notification.query.filter_by(user_id=user.id, lido=False, tipo='geral')
            q_os = Notification.query.filter_by(user_id=user.id, lido=False, tipo='os')

            general_count = q_general.count()
            os_count = q_os.count()

            general_list = (
                q_general.order_by(Notification.created_at.desc())
                        .limit(10)
                        .all()
            )

            os_list = (
                q_os.order_by(Notification.created_at.desc())
                     .limit(10)
                     .all()
            )

            return {
                'notificacoes': general_count,
                'notificacoes_list': general_list,
                'os_notificacoes': os_count,
                'os_notificacoes_list': os_list,
            }
    return {
        'notificacoes': 0,
        'notificacoes_list': [],
        'os_notificacoes': 0,
        'os_notificacoes_list': [],
    }

@app.context_processor
def inject_enums():
    return dict(ArticleStatus=ArticleStatus, Permissao=Permissao)

@app.context_processor
def inject_current_user():
    if 'user_id' in session:
        return {'current_user': User.query.get(session['user_id'])}
    return {'current_user': None}

@app.context_processor
def inject_zoneinfo():
    return dict(ZoneInfo=ZoneInfo)

@app.context_processor
def inject_niveis_cargo():
    """Disponibiliza o mapeamento de níveis hierárquicos para todos os templates."""
    return dict(NOME_NIVEL_CARGO=NOME_NIVEL_CARGO, NIVEIS_HIERARQUICOS=NIVEIS_HIERARQUICOS)

