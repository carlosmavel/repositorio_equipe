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
import click
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash # generate_password_hash se for resetar senha no admin
from sqlalchemy import or_, func
#from models import user_funcoes

try:
    from .config import Config
except ImportError:  # pragma: no cover - fallback for direct execution
    from config import Config
try:
    from .core.database import db
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.database import db
try:
    from .core.enums import ArticleStatus, ArticleVisibility, Permissao
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.enums import ArticleStatus, ArticleVisibility, Permissao

try:
    from .core.models import (
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
    from core.models import (
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
    from .core.utils import (
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
    from core.utils import (
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
try:
    from .seeds.bootstrap_admin import ensure_initial_admin
except ImportError:  # pragma: no cover - fallback for direct execution
    from seeds.bootstrap_admin import ensure_initial_admin


try:
    from .core.services.permission_sync import sync_permission_catalog_with_lock
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.services.permission_sync import sync_permission_catalog_with_lock

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
app.config.from_object(Config)

app.secret_key = app.config['SECRET_KEY']
app.logger.info(
    "SECRET_KEY carregada do ambiente: %s...%s",
    app.secret_key[:5],
    app.secret_key[-5:],
)

database_uri = app.config['SQLALCHEMY_DATABASE_URI']
uri_parts_test = database_uri.split('@')
if len(uri_parts_test) == 2:
    scheme = database_uri.split('://')[0]
    creds_part_test = uri_parts_test[0].split(':')
    user_part_test = creds_part_test[0].split('//')[-1]
    printed_uri_test = f"{scheme}://{user_part_test}:[SENHA_OCULTA]@{uri_parts_test[1]}"
    app.logger.info("DATABASE_URI carregada do ambiente: %s", printed_uri_test)
else:
    app.logger.info("DATABASE_URI carregada do ambiente: %s", database_uri)

db.init_app(app)
migrate = Migrate(app, db)

try:
    from .blueprints.admin import admin_bp
    from .blueprints.auth import auth_bp
    from .blueprints.articles import articles_bp
except ImportError:  # pragma: no cover - fallback for direct execution
    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp
    from blueprints.articles import articles_bp


app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(articles_bp)

for rule in list(app.url_map.iter_rules()):
    if rule.endpoint.startswith('admin_bp.') or rule.endpoint.startswith('auth_bp.') or rule.endpoint.startswith('articles_bp.'):
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



@app.cli.command("bootstrap-permissions")
def bootstrap_permissions_command() -> None:
    """Sincroniza o catálogo centralizado de permissões (idempotente)."""
    result = sync_permission_catalog_with_lock(db.session)
    db.session.commit()

    if result is None:
        click.echo("ℹ️ Sincronização de permissões ignorada (lock não adquirido).")
        return

    click.echo(
        "✅ Catálogo de permissões sincronizado. "
        f"created={result.created} updated={result.updated} unchanged={result.unchanged}"
    )


def _should_run_startup_bootstrap() -> bool:
    if app.config.get('TESTING'):
        return False

    enabled = str(os.getenv('RUN_STARTUP_BOOTSTRAP', '1')).strip().lower()
    if enabled in {'0', 'false', 'no'}:
        return False

    if app.debug:
        return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    return True


@app.before_request
def _run_startup_permission_bootstrap_once() -> None:
    if app.config.get('_permission_bootstrap_done'):
        return
    if not _should_run_startup_bootstrap():
        app.config['_permission_bootstrap_done'] = True
        return

    result = sync_permission_catalog_with_lock(db.session)
    db.session.commit()

    if result is None:
        app.logger.info(
            'permission_catalog_sync_skipped',
            extra={'event': 'permission_catalog_sync_skipped', 'reason': 'lock_not_acquired'},
        )
    else:
        app.logger.info(
            'permission_catalog_sync_completed',
            extra={
                'event': 'permission_catalog_sync_completed',
                'created_count': result.created,
                'updated_count': result.updated,
                'unchanged_count': result.unchanged,
            },
        )

    app.config['_permission_bootstrap_done'] = True

@app.cli.command("bootstrap-admin")
@click.option("--username", default="admin", show_default=True, help="Username do admin inicial.")
@click.option("--email", default="admin@seudominio.com", show_default=True, help="E-mail do admin inicial.")
@click.option("--password", default=None, help="Senha inicial. Se omitida, será gerada com segurança e exibida no terminal.")
@click.option("--nome-completo", "nome_completo", default="Administrador Inicial", show_default=True, help="Nome completo do admin inicial.")
def bootstrap_admin_command(username: str, email: str, password: str | None, nome_completo: str) -> None:
    """Cria (ou garante) o usuário administrador inicial de forma idempotente."""
    result = ensure_initial_admin(
        username=username,
        email=email,
        initial_password=password,
        nome_completo=nome_completo,
    )

    if result.created:
        click.echo("✅ Admin inicial criado com sucesso.")
        click.echo(f"- username: {result.user.username}")
        click.echo(f"- email: {result.user.email}")
        if result.generated_password:
            click.echo(f"- senha temporária gerada: {result.generated_password}")
        else:
            click.echo("- senha temporária: [informada via --password]")
        click.echo("- deve_trocar_senha: True")
    else:
        click.echo("ℹ️ Admin inicial já existe (idempotente, nenhum duplicado criado).")
        click.echo(f"- username: {result.user.username}")
        click.echo("- deve_trocar_senha: True")



def _is_auth_local_flash_path(path: str) -> bool:
    if not path:
        return False
    return (
        path in {'/login', '/esqueci-senha'}
        or path.startswith('/reset-senha/')
        or path.startswith('/criar-senha/')
    )


@app.context_processor
def inject_layout_flags():
    current_path = request.path if request else ''
    return {
        'is_auth_local_flash_page': _is_auth_local_flash_path(current_path),
    }

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
        .filter_by(user_id=session['user_id'], tipo='geral')
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify([
        {'id': n.id, 'message': n.message, 'url': n.url, 'lido': n.lido}
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
    from .core.decorators import admin_required
except ImportError:  # pragma: no cover
    from core.decorators import admin_required

# -------------------------------------------------------------------------
# Context Processors
# -------------------------------------------------------------------------
@app.context_processor
def inject_notificacoes():
    if 'user_id' in session: # Usar user_id é mais seguro que username para buscar no banco
        user = User.query.get(session['user_id']) # Usar .get() é mais direto para PK
        if user:
            q_general_unread = Notification.query.filter_by(user_id=user.id, lido=False, tipo='geral')
            general_count = q_general_unread.count()

            general_list = (
                Notification.query
                .filter_by(user_id=user.id, tipo='geral')
                .order_by(Notification.created_at.desc())
                .limit(10)
                .all()
            )

            return {
                'notificacoes': general_count,
                'notificacoes_list': general_list,
            }
    return {
        'notificacoes': 0,
        'notificacoes_list': [],
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

