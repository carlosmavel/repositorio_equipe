# app.py

# -------------------------------------------------------------------------
# IMPORTS (Mantendo os seus e garantindo os necessários)
# -------------------------------------------------------------------------
import os
import json
import time
import uuid
import hashlib
import re # Você já tinha, bom para futuras validações
import sys
from datetime import datetime, timezone # Adicionei datetime aqui se for usar em 'strptime' na rota de perfil
from pathlib import Path
from zoneinfo import ZoneInfo # Você já tinha
from urllib.parse import urlsplit, urlunsplit

from flask import (
    Flask, request, render_template, redirect, url_for,
    session, send_from_directory, flash, jsonify # Adicionei jsonify se for usar em APIs futuras
)
import logging
import click
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash # generate_password_hash se for resetar senha no admin
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
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
        Boletim,
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
        Boletim,
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
try:
    from .core.services.ocr_queue import process_pending_ocr_items
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.services.ocr_queue import process_pending_ocr_items

from mimetypes import guess_type # Se for usar, descomente

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
app.config.from_object(Config)


def _is_homologacao_environment() -> bool:
    env_name = (
        os.getenv('APP_ENV')
        or os.getenv('FLASK_ENV')
        or os.getenv('ENVIRONMENT')
        or 'production'
    ).strip().lower()
    return env_name in {'homologacao', 'homolog', 'staging', 'development'}


if _is_homologacao_environment():
    log_level = logging.DEBUG
    logging.basicConfig(
        level=log_level,
        stream=sys.stdout,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
    )
    app.config['SQLALCHEMY_ECHO'] = os.getenv('SQLALCHEMY_ECHO', 'true').lower() == 'true'
else:
    log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        stream=sys.stdout,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
    )
    app.config.setdefault('SQLALCHEMY_ECHO', os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true')

app.logger.setLevel(log_level)
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG if _is_homologacao_environment() else logging.WARNING)

app.secret_key = app.config['SECRET_KEY']
app.logger.info(
    "SECRET_KEY carregada do ambiente: %s...%s",
    app.secret_key[:5],
    app.secret_key[-5:],
)

database_uri = app.config['SQLALCHEMY_DATABASE_URI']
parsed_database_uri = urlsplit(database_uri)

if parsed_database_uri.password is not None:
    host = parsed_database_uri.hostname or ''
    if ':' in host and not host.startswith('['):
        host = f'[{host}]'

    if parsed_database_uri.port is not None:
        host = f'{host}:{parsed_database_uri.port}'

    if parsed_database_uri.username:
        userinfo = f'{parsed_database_uri.username}:[SENHA_OCULTA]@'
    else:
        userinfo = '[SENHA_OCULTA]@'

    masked_database_uri = urlunsplit(
        (
            parsed_database_uri.scheme,
            f'{userinfo}{host}',
            parsed_database_uri.path,
            parsed_database_uri.query,
            parsed_database_uri.fragment,
        )
    )
    app.logger.info("DATABASE_URI carregada do ambiente: %s", masked_database_uri)
else:
    app.logger.info("DATABASE_URI carregada do ambiente: %s", database_uri)

db.init_app(app)
migrate = Migrate(app, db)

try:
    from .blueprints.admin import admin_bp
    from .blueprints.auth import auth_bp
    from .blueprints.articles import articles_bp
    from .blueprints.boletins import boletins_bp
except ImportError:  # pragma: no cover - fallback for direct execution
    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp
    from blueprints.articles import articles_bp
    from blueprints.boletins import boletins_bp


app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(articles_bp)
app.register_blueprint(boletins_bp)

for rule in list(app.url_map.iter_rules()):
    if rule.endpoint.startswith('admin_bp.') or rule.endpoint.startswith('auth_bp.') or rule.endpoint.startswith('articles_bp.') or rule.endpoint.startswith('boletins_bp.'):
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


def _human_readable_size(size_in_bytes: int) -> str:
    """Converte bytes para uma representação curta e amigável."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    if size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.0f} KB"
    return f"{size_in_bytes / (1024 * 1024):.1f} MB"


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(error):
    max_content_length = app.config.get('MAX_CONTENT_LENGTH')

    limite_texto = ''
    if isinstance(max_content_length, int) and max_content_length > 0:
        limite_texto = f" Limite atual: {_human_readable_size(max_content_length)}."

    flash(
        "O arquivo enviado excede o tamanho máximo permitido. "
        f"Reduza o tamanho e tente novamente.{limite_texto}",
        'danger',
    )

    app.logger.warning(
        (
            "HTTP 413 RequestEntityTooLarge | method=%s path=%s endpoint=%s "
            "user_id=%s content_length=%s max_content_length=%s remote_addr=%s"
        ),
        request.method,
        request.path,
        request.endpoint,
        session.get('user_id'),
        request.content_length,
        max_content_length,
        request.remote_addr,
    )

    redirect_target = request.referrer or request.url or url_for('pagina_inicial')
    return redirect(redirect_target)



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


@app.cli.command("process-ocr-pendente")
@click.option("--batch-size", default=20, show_default=True, type=int)
@click.option("--stuck-timeout-minutes", default=30, show_default=True, type=int)
@click.option("--low-yield-threshold", default=80, show_default=True, type=int)
def process_ocr_pendente_command(
    batch_size: int,
    stuck_timeout_minutes: int,
    low_yield_threshold: int,
) -> None:
    """Processa OCR pendente em lote (anexos e boletins) fora da request web."""
    results = process_pending_ocr_items(
        batch_size=batch_size,
        stuck_timeout_minutes=stuck_timeout_minutes,
        low_yield_threshold=low_yield_threshold,
    )
    attachment_result = results["attachments"]
    boletim_result = results["boletins"]

    click.echo(
        "✅ OCR pendente processado. "
        f"attachments(recover={attachment_result.recovered_stuck}, processed={attachment_result.processed}, concluido={attachment_result.concluded}, baixo_aproveitamento={attachment_result.low_yield}, erro={attachment_result.failed}) "
        f"boletins(recover={boletim_result.recovered_stuck}, processed={boletim_result.processed}, concluido={boletim_result.concluded}, baixo_aproveitamento={boletim_result.low_yield}, erro={boletim_result.failed})"
    )


def _parse_boletim_date_from_title(filename_stem: str):
    match = re.search(r"(\d{1,2})_(\d{1,2})_(\d{2}|\d{4})$", filename_stem.strip())
    if not match:
        return None

    day = int(match.group(1))
    month = int(match.group(2))
    year_raw = match.group(3)
    year = int(year_raw)
    if len(year_raw) == 2:
        year += 2000

    try:
        return datetime(year, month, day).date()
    except ValueError:
        return None


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


@app.cli.command("importar-boletins")
@click.option("--pasta", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--admin-email", required=True, type=str)
@click.option("--dry-run", is_flag=True, default=False)
def importar_boletins_command(pasta: Path, admin_email: str, dry_run: bool) -> None:
    """Importa boletins PDF em lote com extração de data no título."""
    admin = User.query.filter(func.lower(User.email) == admin_email.strip().lower()).one_or_none()
    if not admin:
        raise click.ClickException(f"Usuário administrador não encontrado para o e-mail: {admin_email}")

    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted([path for path in pasta.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"])
    click.echo(f"🔎 Arquivos PDF encontrados: {len(pdf_paths)}")

    existing_name_and_size = {
        (row.arquivo or "", os.path.getsize(upload_dir / row.arquivo) if (upload_dir / row.arquivo).exists() else None)
        for row in Boletim.query.with_entities(Boletim.arquivo).all()
    }
    existing_hashes = set()
    for arquivo, _ in existing_name_and_size:
        full_path = upload_dir / arquivo
        if full_path.exists() and full_path.is_file():
            try:
                existing_hashes.add(_file_sha256(full_path))
            except OSError:
                continue

    imported = 0
    duplicated = 0
    errored = 0
    with_date = 0
    without_date = 0

    for pdf_path in pdf_paths:
        titulo = pdf_path.stem
        boletim_date = _parse_boletim_date_from_title(titulo)
        if boletim_date:
            with_date += 1
            date_text = boletim_date.strftime("%d/%m/%Y")
        else:
            without_date += 1
            date_text = "data não identificada"

        try:
            file_hash = _file_sha256(pdf_path)
            duplicate_by_hash = file_hash in existing_hashes
            duplicate_by_name = any((pdf_path.name == item_name) for item_name, _ in existing_name_and_size)
            if duplicate_by_hash or duplicate_by_name:
                duplicated += 1
                click.echo(f"⏭️  Ignorado duplicado: {pdf_path} ({date_text})")
                continue

            dest_filename = secure_filename(pdf_path.name)
            dest_name = dest_filename
            if (upload_dir / dest_name).exists():
                dest_name = f"{uuid.uuid4().hex}_{dest_filename}"

            click.echo(f"📄 Processando: {pdf_path} | data: {date_text}")
            if dry_run:
                imported += 1
                continue

            with pdf_path.open("rb") as src, (upload_dir / dest_name).open("wb") as dst:
                dst.write(src.read())

            data_boletim = boletim_date or datetime.now().date()
            boletim = Boletim(
                titulo=titulo,
                data_boletim=data_boletim,
                arquivo=dest_name,
                created_by=admin.id,
                ocr_status="pendente",
            )
            db.session.add(boletim)
            db.session.flush()

            imported += 1
            existing_hashes.add(file_hash)
            existing_name_and_size.add((dest_name, os.path.getsize(upload_dir / dest_name)))
        except Exception as exc:
            errored += 1
            click.echo(f"❌ Erro ao processar {pdf_path}: {exc}")
            if not dry_run:
                db.session.rollback()

    if not dry_run:
        db.session.commit()

    click.echo("")
    click.echo("📊 Resumo da importação de boletins")
    click.echo(f"- total de arquivos encontrados: {len(pdf_paths)}")
    click.echo(f"- total importado: {imported}")
    click.echo(f"- total ignorado (duplicidade): {duplicated}")
    click.echo(f"- total com erro: {errored}")
    click.echo(f"- total com data identificada: {with_date}")
    click.echo(f"- total sem data: {without_date}")
    click.echo(f"- modo dry-run: {'sim' if dry_run else 'não'}")


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
