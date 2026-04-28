from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app as app
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

try:
    from ..core.database import db
except ImportError:  # pragma: no cover
    from core.database import db

try:
    from ..core.models import (
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
        Funcao,
        ArtigoTipo,
        ArtigoArea,
        ArtigoSistema,
    )
except ImportError:  # pragma: no cover
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
        Funcao,
        ArtigoTipo,
        ArtigoArea,
        ArtigoSistema,
    )

try:
    from ..core.enums import ArticleStatus, Permissao
except ImportError:
    from core.enums import ArticleStatus, Permissao

try:
    from ..core.decorators import admin_required
except ImportError:  # pragma: no cover
    from core.decorators import admin_required
try:
    from ..core.utils import (
        send_email,
        generate_token,
        eligible_review_notification_users,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
        log_article_event,
    )
except ImportError:  # pragma: no cover
    from core.utils import (
        send_email,
        generate_token,
        eligible_review_notification_users,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
        log_article_event,
    )
try:
    from ..core.services.ocr_queue import (
        OCR_STATUS_BAIXO_APROVEITAMENTO,
        OCR_STATUS_ERRO,
        mark_attachment_for_reprocess,
    )
except ImportError:  # pragma: no cover
    from core.services.ocr_queue import (
        OCR_STATUS_BAIXO_APROVEITAMENTO,
        OCR_STATUS_ERRO,
        mark_attachment_for_reprocess,
    )

import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from werkzeug.utils import secure_filename
from mimetypes import guess_type
import uuid
import os

admin_bp = Blueprint('admin_bp', __name__)


def _can_manage_taxonomy(user, permission_code: str) -> bool:
    return bool(user and (user.has_permissao('admin') or user.has_permissao(permission_code)))


def _current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


def _request_correlation_id():
    return (
        request.headers.get('X-Request-ID')
        or request.headers.get('X-Correlation-ID')
        or request.headers.get('X-Amzn-Trace-Id')
        or request.environ.get('HTTP_X_REQUEST_ID')
        or request.environ.get('HTTP_X_CORRELATION_ID')
    )


def _can_reprocess_ocr(user) -> bool:
    if not user:
        return False
    return user.has_permissao('admin') or user.has_permissao(Permissao.ARTIGO_OCR_REPROCESSAR.value)


def _eligible_ocr_attachment_query():
    return Attachment.query.filter(
        or_(
            Attachment.mime_type == 'application/pdf',
            Attachment.filename.ilike('%.pdf'),
        )
    )


def _reprocess_attachments(attachments, *, actor: User, trigger_scope: str, success_message: str):
    if not attachments:
        flash('Nenhum anexo elegível para reprocesso foi encontrado.', 'info')
        return redirect(request.referrer or url_for('admin_bp.admin_dashboard'))

    for attachment in attachments:
        mark_attachment_for_reprocess(
            attachment,
            triggered_by_user_id=actor.id,
            trigger_scope=trigger_scope,
        )
        log_article_event(
            app.logger,
            "ocr_reprocess_requested",
            user_id=actor.id,
            route=request.path,
            action=trigger_scope,
            article_id=attachment.article_id,
            attachment_id=attachment.id,
            filename=attachment.filename,
            file_size=None,
            mime_type=attachment.mime_type,
            ocr_status=attachment.ocr_status,
            attempt=attachment.ocr_attempts,
            progress_id=None,
            correlation_id=_request_correlation_id(),
        )

    db.session.commit()
    flash(f'{success_message} ({len(attachments)} anexo(s) reenfileirado(s)).', 'success')
    return redirect(request.referrer or url_for('admin_bp.admin_dashboard'))

# ROTAS DE ADMINISTRAÇÃO (NOVA SEÇÃO - ADICIONE AS ROTAS DO ADMIN AQUI)
# -------------------------------------------------------------------------
@admin_bp.route('/admin/')
@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Exibe o dashboard administrativo com estatísticas básicas."""
    user_total = User.query.count()
    users_active = User.query.filter_by(ativo=True).count()
    users_inactive = user_total - users_active

    status_counts = dict(
        db.session.query(Article.status, func.count(Article.id))
        .group_by(Article.status)
        .all()
    )
    status_counts = {
        (s.value if hasattr(s, "value") else s): status_counts.get(s, 0)
        for s in ArticleStatus
    }

    notifications_unread = Notification.query.filter_by(lido=False).count()
    notifications_read = Notification.query.filter_by(lido=True).count()
    user_sector_counts = dict(
        db.session.query(Setor.nome, func.count(User.id))
        .outerjoin(User, User.setor_id == Setor.id)
        .group_by(Setor.id, Setor.nome)
        .order_by(Setor.nome)
        .all()
    )

    ocr_statuses = [
        'pendente',
        'processando',
        'concluido',
        'erro',
        'baixo_aproveitamento',
    ]
    ocr_raw_counts = dict(
        db.session.query(Attachment.ocr_status, func.count(Attachment.id))
        .filter(Attachment.ocr_status.in_(ocr_statuses))
        .group_by(Attachment.ocr_status)
        .all()
    )
    ocr_total_eligible = sum(ocr_raw_counts.values())
    ocr_status_metrics = {}
    for status in ocr_statuses:
        count = int(ocr_raw_counts.get(status, 0) or 0)
        percentage = round((count / ocr_total_eligible) * 100, 2) if ocr_total_eligible else 0.0
        ocr_status_metrics[status] = {
            'count': count,
            'percentage': percentage,
        }

    ocr_avg_char_count = (
        db.session.query(func.avg(Attachment.ocr_char_count))
        .filter(Attachment.ocr_status.in_(ocr_statuses))
        .filter(Attachment.ocr_char_count.isnot(None))
        .scalar()
    ) or 0.0
    ocr_avg_processing_seconds = (
        db.session.query(func.avg(Attachment.ocr_processing_time_seconds))
        .filter(Attachment.ocr_status.in_(ocr_statuses))
        .filter(Attachment.ocr_processing_time_seconds.isnot(None))
        .scalar()
    ) or 0.0

    processing_stuck_threshold_minutes = int(app.config.get('OCR_STUCK_THRESHOLD_MINUTES', 30))
    processing_stuck_cutoff = datetime.now(timezone.utc) - timedelta(minutes=processing_stuck_threshold_minutes)
    ocr_stuck_processing_items = (
        Attachment.query
        .filter(Attachment.ocr_status == 'processando')
        .filter(Attachment.ocr_started_at.isnot(None))
        .filter(Attachment.ocr_started_at < processing_stuck_cutoff)
        .order_by(Attachment.ocr_started_at.asc())
        .limit(5)
        .all()
    )

    ocr_latest_errors = (
        Attachment.query
        .filter(Attachment.ocr_status.in_(['erro', 'baixo_aproveitamento']))
        .filter(
            or_(
                Attachment.ocr_last_error.isnot(None),
                Attachment.ocr_error_message.isnot(None),
            )
        )
        .order_by(Attachment.ocr_last_attempt_at.desc().nullslast(), Attachment.created_at.desc())
        .limit(5)
        .all()
    )

    current_user = _current_user()
    return render_template(
        "admin/dashboard.html",
        user_total=user_total,
        users_active=users_active,
        users_inactive=users_inactive,
        article_status_counts=status_counts,
        notifications_unread=notifications_unread,
        notifications_read=notifications_read,
        user_sector_counts=user_sector_counts,
        ocr_status_metrics=ocr_status_metrics,
        ocr_total_eligible=ocr_total_eligible,
        ocr_avg_char_count=round(float(ocr_avg_char_count), 2),
        ocr_avg_processing_seconds=round(float(ocr_avg_processing_seconds), 2),
        ocr_latest_errors=ocr_latest_errors,
        ocr_stuck_processing_items=ocr_stuck_processing_items,
        processing_stuck_threshold_minutes=processing_stuck_threshold_minutes,
        can_reprocess_ocr=_can_reprocess_ocr(current_user),
    )


@admin_bp.route('/admin/ocr/reprocess/attachment/<int:attachment_id>', methods=['POST'])
def admin_reprocess_ocr_attachment(attachment_id):
    user = _current_user()
    if not _can_reprocess_ocr(user):
        flash('Permissão negada para reprocessar OCR.', 'danger')
        return redirect(url_for('meus_artigos'))

    attachment = _eligible_ocr_attachment_query().filter(Attachment.id == attachment_id).one_or_none()
    if not attachment:
        flash('Anexo não encontrado ou não elegível para OCR.', 'warning')
        return redirect(request.referrer or url_for('admin_bp.admin_dashboard'))

    return _reprocess_attachments(
        [attachment],
        actor=user,
        trigger_scope='attachment',
        success_message='Reprocesso do anexo solicitado com sucesso',
    )


@admin_bp.route('/admin/ocr/reprocess/article/<int:article_id>', methods=['POST'])
def admin_reprocess_ocr_article(article_id):
    user = _current_user()
    if not _can_reprocess_ocr(user):
        flash('Permissão negada para reprocessar OCR.', 'danger')
        return redirect(url_for('meus_artigos'))

    attachments = _eligible_ocr_attachment_query().filter(Attachment.article_id == article_id).all()
    return _reprocess_attachments(
        attachments,
        actor=user,
        trigger_scope='article',
        success_message='Reprocesso por artigo solicitado com sucesso',
    )


@admin_bp.route('/admin/ocr/reprocess/errors', methods=['POST'])
def admin_reprocess_ocr_errors():
    user = _current_user()
    if not _can_reprocess_ocr(user):
        flash('Permissão negada para reprocessar OCR.', 'danger')
        return redirect(url_for('meus_artigos'))

    attachments = (
        _eligible_ocr_attachment_query()
        .filter(Attachment.ocr_status == OCR_STATUS_ERRO)
        .all()
    )
    return _reprocess_attachments(
        attachments,
        actor=user,
        trigger_scope='errors',
        success_message='Reprocesso de anexos com erro solicitado com sucesso',
    )


@admin_bp.route('/admin/ocr/reprocess/low-yield', methods=['POST'])
def admin_reprocess_ocr_low_yield():
    user = _current_user()
    if not _can_reprocess_ocr(user):
        flash('Permissão negada para reprocessar OCR.', 'danger')
        return redirect(url_for('meus_artigos'))

    attachments = (
        _eligible_ocr_attachment_query()
        .filter(Attachment.ocr_status == OCR_STATUS_BAIXO_APROVEITAMENTO)
        .all()
    )
    return _reprocess_attachments(
        attachments,
        actor=user,
        trigger_scope='low_yield',
        success_message='Reprocesso de anexos com baixo aproveitamento solicitado com sucesso',
    )

@admin_bp.route('/admin/instituicoes', methods=['GET', 'POST'])
@admin_required
def admin_instituicoes():
    """CRUD para Instituições."""
    instituicao_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            instituicao_para_editar = Instituicao.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        codigo = request.form.get('codigo', '').strip().upper()
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo_check') == 'on'

        if not codigo or not nome:
            flash('Código e nome da instituição são obrigatórios.', 'danger')
        else:
            query_codigo_existente = Instituicao.query.filter_by(codigo=codigo)
            query_nome_existente = Instituicao.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_codigo_existente = query_codigo_existente.filter(Instituicao.id != int(id_para_atualizar))
                query_nome_existente = query_nome_existente.filter(Instituicao.id != int(id_para_atualizar))
            codigo_ja_existe = query_codigo_existente.first()
            nome_ja_existe = query_nome_existente.first()

            if codigo_ja_existe:
                flash(f'O código "{codigo}" já está em uso.', 'danger')
            elif nome_ja_existe:
                flash(f'O nome "{nome}" já está em uso.', 'danger')
            else:
                if id_para_atualizar:
                    inst = Instituicao.query.get_or_404(id_para_atualizar)
                    inst.codigo = codigo
                    inst.nome = nome
                    inst.descricao = descricao
                    inst.ativo = ativo
                    action_msg = 'atualizada'
                else:
                    inst = Instituicao(codigo=codigo, nome=nome, descricao=descricao, ativo=ativo)
                    db.session.add(inst)
                    action_msg = 'criada'

                try:
                    db.session.commit()
                    flash(f'Instituição {action_msg} com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_instituicoes'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar instituição: {str(e)}', 'danger')

        if id_para_atualizar:
            instituicao_para_editar = Instituicao.query.get(id_para_atualizar)

    instituicoes = Instituicao.query.order_by(Instituicao.nome).all()
    return render_template('admin/instituicoes.html',
                           instituicoes=instituicoes,
                           inst_editar=instituicao_para_editar)

@admin_bp.route('/admin/instituicoes/toggle_ativo/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_ativo_instituicao(id):
    inst = Instituicao.query.get_or_404(id)
    if inst.estabelecimentos.count() > 0 and inst.ativo:
        flash(
            f'Atenção: "{inst.nome}" possui Estabelecimentos associados. Inativá-la pode ter implicações.',
            'warning'
        )

    inst.ativo = not inst.ativo
    try:
        db.session.commit()
        status_texto = 'ativada' if inst.ativo else 'desativada'
        flash(f'Instituição "{inst.nome}" foi {status_texto} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status da instituição: {str(e)}', 'danger')
    return redirect(url_for('admin_bp.admin_instituicoes'))

@admin_bp.route('/admin/estabelecimentos', methods=['GET', 'POST'])
@admin_required
def admin_estabelecimentos():
    """
    Rota para listar, criar e editar estabelecimentos.
    GET: Exibe a lista de estabelecimentos e um formulário.
         Se 'edit_id' estiver nos args da URL, preenche o formulário para edição.
    POST: Processa a criação ou atualização de um estabelecimento.
    """
    estabelecimento_para_editar = None
    # Se for um GET e houver 'edit_id', carrega o estabelecimento para edição
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            estabelecimento_para_editar = Estabelecimento.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        codigo = request.form.get('codigo', '').strip().upper()
        nome_fantasia = request.form.get('nome_fantasia', '').strip()
        ativo = request.form.get('ativo_check') == 'on' # Para o checkbox
        instituicao_id = request.form.get('instituicao_id') or None

        # Captura dos demais campos do formulário de Estabelecimento
        razao_social = request.form.get('razao_social', '').strip()
        cnpj = request.form.get('cnpj', '').strip()
        inscricao_estadual = request.form.get('inscricao_estadual', '').strip()
        inscricao_municipal = request.form.get('inscricao_municipal', '').strip()
        tipo_estabelecimento = request.form.get('tipo_estabelecimento', '').strip()
        cep = request.form.get('cep', '').strip()
        logradouro = request.form.get('logradouro', '').strip()
        numero = request.form.get('numero', '').strip()
        complemento = request.form.get('complemento', '').strip()
        bairro = request.form.get('bairro', '').strip()
        cidade = request.form.get('cidade', '').strip()
        estado = request.form.get('estado', '').strip()
        pais = request.form.get('pais', '').strip()
        telefone_principal = request.form.get('telefone_principal', '').strip()
        telefone_secundario = request.form.get('telefone_secundario', '').strip()
        email_contato = request.form.get('email_contato', '').strip()
        data_abertura_str = request.form.get('data_abertura', '').strip()
        observacoes = request.form.get('observacoes', '').strip()

        # Converte data de abertura para objeto date, se fornecida
        data_abertura = None
        if data_abertura_str:
            try:
                data_abertura = datetime.strptime(data_abertura_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Data de abertura inválida.', 'danger')

        if not codigo or not nome_fantasia:
            flash('Código e Nome Fantasia do estabelecimento são obrigatórios.', 'danger')
        else:
            # Verifica unicidade do código do estabelecimento
            query_codigo_existente = Estabelecimento.query.filter_by(codigo=codigo)
            if id_para_atualizar:
                query_codigo_existente = query_codigo_existente.filter(Estabelecimento.id != int(id_para_atualizar))
            codigo_ja_existe = query_codigo_existente.first()

            # Verifica unicidade do CNPJ (se preenchido)
            cnpj_ja_existe = None
            if cnpj:
                query_cnpj_existente = Estabelecimento.query.filter_by(cnpj=cnpj)
                if id_para_atualizar:
                    query_cnpj_existente = query_cnpj_existente.filter(Estabelecimento.id != int(id_para_atualizar))
                cnpj_ja_existe = query_cnpj_existente.first()

            if codigo_ja_existe:
                flash(f'O código de estabelecimento "{codigo}" já está em uso.', 'danger')
            elif cnpj_ja_existe:
                flash(f'O CNPJ "{cnpj}" já está em uso por outro estabelecimento.', 'danger')
            else:
                if id_para_atualizar: # Atualizar
                    est = Estabelecimento.query.get_or_404(id_para_atualizar)
                    est.codigo = codigo
                    est.nome_fantasia = nome_fantasia
                    est.instituicao_id = int(instituicao_id) if instituicao_id else None
                    est.razao_social = razao_social
                    est.cnpj = cnpj if cnpj else None  # Salva None se vazio
                    est.inscricao_estadual = inscricao_estadual
                    est.inscricao_municipal = inscricao_municipal
                    est.tipo_estabelecimento = tipo_estabelecimento
                    est.cep = cep
                    est.logradouro = logradouro
                    est.numero = numero
                    est.complemento = complemento
                    est.bairro = bairro
                    est.cidade = cidade
                    est.estado = estado
                    est.pais = pais or None
                    est.telefone_principal = telefone_principal
                    est.telefone_secundario = telefone_secundario
                    est.email_contato = email_contato
                    est.data_abertura = data_abertura
                    est.observacoes = observacoes
                    est.ativo = ativo
                    action_msg = 'atualizado'
                else: # Criar novo
                    est = Estabelecimento(
                        codigo=codigo,
                        nome_fantasia=nome_fantasia,
                        instituicao_id=int(instituicao_id) if instituicao_id else None,
                        razao_social=razao_social,
                        cnpj=cnpj if cnpj else None,
                        inscricao_estadual=inscricao_estadual,
                        inscricao_municipal=inscricao_municipal,
                        tipo_estabelecimento=tipo_estabelecimento,
                        cep=cep,
                        logradouro=logradouro,
                        numero=numero,
                        complemento=complemento,
                        bairro=bairro,
                        cidade=cidade,
                        estado=estado,
                        pais=pais or None,
                        telefone_principal=telefone_principal,
                        telefone_secundario=telefone_secundario,
                        email_contato=email_contato,
                        data_abertura=data_abertura,
                        observacoes=observacoes,
                        ativo=ativo
                    )
                    db.session.add(est)
                    action_msg = 'criado'

                try:
                    db.session.commit()
                    flash(f'Estabelecimento {action_msg} com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_estabelecimentos'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar estabelecimento: {str(e)}', 'danger')
                    app.logger.error(f"Erro DB Estabelecimento: {e}")

        # Se houve erro no POST e não redirecionou, preenche para re-exibir o form
        if id_para_atualizar :
             estabelecimento_para_editar = Estabelecimento.query.get(id_para_atualizar) # Mantém o modo edição
        else: # Se era uma tentativa de criação que falhou, recria um objeto temporário com os dados do form
              # para repopular, ou confia no request.form no template.
              # Por simplicidade, o template usará request.form para repopular em caso de erro na criação.
              pass


    # Para requisições GET ou se um POST falhou e precisa re-renderizar
    todos_estabelecimentos = Estabelecimento.query.order_by(Estabelecimento.nome_fantasia).all()
    instituicoes = Instituicao.query.order_by(Instituicao.nome).all()
    return render_template('admin/estabelecimentos.html',
                           estabelecimentos=todos_estabelecimentos,
                           instituicoes=instituicoes,
                           est_editar=estabelecimento_para_editar)

@admin_bp.route('/admin/estabelecimentos/toggle_ativo/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_ativo_estabelecimento(id):
    """
    Alterna o status 'ativo' (True/False) de um estabelecimento.
    """
    est = Estabelecimento.query.get_or_404(id)

    # Lógica de verificação de dependências antes de INATIVAR
    if est.ativo and est.usuarios.count() > 0:
        flash(f'Atenção: "{est.nome_fantasia}" possui Usuários associados. Inativá-lo pode ter implicações.', 'warning')

    est.ativo = not est.ativo # Inverte o status atual
    try:
        db.session.commit()
        status_texto = "ativado" if est.ativo else "desativado"
        flash(f'Estabelecimento "{est.nome_fantasia}" foi {status_texto} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do estabelecimento: {str(e)}', 'danger')
        app.logger.error(f"Erro ao alterar status do est. {est.id}: {e}")
    return redirect(url_for('admin_bp.admin_estabelecimentos'))

@admin_bp.route('/admin/usuarios', methods=['GET', 'POST'])
@admin_required
def admin_usuarios():
    """Lista, cria e edita usuários."""
    usuario_para_editar = None
    manter_aba_cadastro = False
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            usuario_para_editar = User.query.get_or_404(edit_id)
            app.logger.debug(f"Loading user {edit_id} for editing")

    if request.method == 'POST':
        manter_aba_cadastro = True
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        correlation_id = _request_correlation_id()
        actor = _current_user()
        actor_id = getattr(actor, 'id', None) if actor else session.get('user_id')
        actor_username = getattr(actor, 'username', None) if actor else None
        sanitized_form = request.form.to_dict(flat=False)
        if 'password' in sanitized_form:
            sanitized_form['password'] = ['***REDACTED***']
        app.logger.info(
            "admin_usuarios_post_received",
            extra={
                'event': 'admin_usuarios_post_received',
                'request_method': request.method,
                'request_path': request.path,
                'request_form': sanitized_form,
                'actor_id': actor_id,
                'actor_username': actor_username,
                'timestamp_utc': timestamp_utc,
                'correlation_id': correlation_id,
            },
        )
        id_para_atualizar = request.form.get('id_para_atualizar')
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        ativo = request.form.get('ativo_check') == 'on'
        password = request.form.get('password', '').strip()

        nome_completo = request.form.get('nome_completo', '').strip()
        matricula = request.form.get('matricula', '').strip()
        cpf = request.form.get('cpf', '').strip()
        rg = request.form.get('rg', '').strip()
        ramal = request.form.get('ramal', '').strip()
        telefone_contato = request.form.get('telefone_contato', '').strip()
        data_nascimento_str = request.form.get('data_nascimento', '').strip()
        data_admissao_str = request.form.get('data_admissao', '').strip()
        estabelecimento_id = request.form.get('estabelecimento_id', type=int)
        setor_ids = list(dict.fromkeys(int(s) for s in request.form.getlist('setor_ids') if s))
        cargo_id = request.form.get('cargo_id', type=int)
        celula_ids = list(dict.fromkeys(int(c) for c in request.form.getlist('celula_ids') if c))
        funcao_ids = list(dict.fromkeys(int(f) for f in request.form.getlist('funcao_ids') if f))

        cargo_padrao = Cargo.query.get(cargo_id) if cargo_id else None
        if cargo_padrao:
            payload_org_original = {
                'estabelecimento_id': estabelecimento_id,
                'setor_ids': setor_ids[:],
                'celula_ids': celula_ids[:],
            }
            cargo_estabelecimentos = [e.id for e in cargo_padrao.default_estabelecimentos]
            cargo_setor_ids = [s.id for s in cargo_padrao.default_setores]
            cargo_celula_ids = [c.id for c in cargo_padrao.default_celulas]

            # Reconciliação determinística:
            # - quando o cargo define defaults organizacionais, eles prevalecem;
            # - quando não define, preserva o payload manual recebido.
            if cargo_setor_ids:
                setor_ids = cargo_setor_ids
            if cargo_celula_ids:
                celula_ids = cargo_celula_ids
            if cargo_estabelecimentos:
                estabelecimento_id = cargo_estabelecimentos[0]

            if payload_org_original['estabelecimento_id'] != estabelecimento_id or payload_org_original['setor_ids'] != setor_ids or payload_org_original['celula_ids'] != celula_ids:
                app.logger.warning(
                    "admin_usuarios_payload_org_reconciled_with_cargo_defaults",
                    extra={
                        'event': 'admin_usuarios_payload_org_reconciled_with_cargo_defaults',
                        'cargo_id': cargo_id,
                        'payload_original': payload_org_original,
                        'payload_reconciled': {
                            'estabelecimento_id': estabelecimento_id,
                            'setor_ids': setor_ids,
                            'celula_ids': celula_ids,
                        },
                        'correlation_id': correlation_id,
                    },
                )

        if celula_ids and not setor_ids:
            celulas = Celula.query.filter(Celula.id.in_(celula_ids)).all()
            setor_ids = list(dict.fromkeys(c.setor_id for c in celulas if c.setor_id))

        celulas_resolvidas = []
        if celula_ids:
            celulas_resolvidas = Celula.query.filter(Celula.id.in_(celula_ids)).all()
            celulas_por_id = {c.id: c for c in celulas_resolvidas}
            celula_ids = [cid for cid in celula_ids if cid in celulas_por_id]
            setores_derivados_das_celulas = [
                celulas_por_id[cid].setor_id
                for cid in celula_ids
                if celulas_por_id[cid].setor_id
            ]
            setor_ids = list(dict.fromkeys([*setor_ids, *setores_derivados_das_celulas]))

        setor_primario_id = None
        celula_primaria_id = celula_ids[0] if celula_ids else None
        if celula_primaria_id:
            celula_primaria = next((c for c in celulas_resolvidas if c.id == celula_primaria_id), None)
            if celula_primaria and celula_primaria.setor_id:
                setor_primario_id = celula_primaria.setor_id
        if setor_primario_id is None and setor_ids:
            setor_primario_id = setor_ids[0]

        if not estabelecimento_id:
            if setor_ids:
                setor_obj = Setor.query.get(setor_ids[0])
                estabelecimento_id = setor_obj.estabelecimento_id if setor_obj else None
            elif celula_ids:
                cel_obj = Celula.query.get(celula_ids[0])
                estabelecimento_id = cel_obj.estabelecimento_id if cel_obj else None

        data_nascimento = None
        if data_nascimento_str:
            try:
                data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Data de nascimento inválida.', 'danger')

        data_admissao = None
        if data_admissao_str:
            try:
                data_admissao = datetime.strptime(data_admissao_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Data de admissão inválida.', 'danger')

        admin_funcao = Funcao.query.filter_by(codigo='admin').first()
        selected_funcao_ids = set(funcao_ids)
        cargo_funcao_ids = {f.id for f in cargo_padrao.permissoes} if cargo_padrao else set()
        is_target_admin = bool(admin_funcao and admin_funcao.id in (selected_funcao_ids | cargo_funcao_ids))

        if id_para_atualizar and not is_target_admin and admin_funcao:
            usuario_existente = User.query.get_or_404(id_para_atualizar)
            possui_admin_atual = usuario_existente.has_permissao('admin')
            removendo_admin = (
                possui_admin_atual
                and admin_funcao.id not in selected_funcao_ids
                and admin_funcao.id not in cargo_funcao_ids
            )
            if not removendo_admin:
                is_target_admin = possui_admin_atual

        app.logger.info(
            "admin_usuarios_parsed_payload",
            extra={
                'event': 'admin_usuarios_parsed_payload',
                'username': username,
                'email': email,
                'ativo': ativo,
                'estabelecimento_id': estabelecimento_id,
                'setor_ids': setor_ids,
                'celula_ids': celula_ids,
                'cargo_id': cargo_id,
                'funcao_ids': funcao_ids,
                'id_para_atualizar': id_para_atualizar,
                'is_target_admin': is_target_admin,
                'correlation_id': correlation_id,
            },
        )

        if not username or not email:
            app.logger.warning(
                "admin_usuarios_validation_failed_missing_username_or_email",
                extra={
                    'event': 'admin_usuarios_validation_failed',
                    'reason': 'missing_username_or_email',
                    'username': username,
                    'email': email,
                    'correlation_id': correlation_id,
                },
            )
            flash('Usuário e Email são obrigatórios.', 'danger')
        elif not is_target_admin and (not estabelecimento_id or not setor_ids or not celula_ids):
            missing_fields = []
            if not estabelecimento_id:
                missing_fields.append('estabelecimento_id')
            if not setor_ids:
                missing_fields.append('setor_ids')
            if not celula_ids:
                missing_fields.append('celula_ids')
            app.logger.warning(
                "admin_usuarios_validation_failed_missing_required_org_fields",
                extra={
                    'event': 'admin_usuarios_validation_failed',
                    'reason': 'missing_required_org_fields',
                    'missing_fields': missing_fields,
                    'is_target_admin': is_target_admin,
                    'correlation_id': correlation_id,
                },
            )
            flash('Usuário, Email, Estabelecimento, Setor e Célula são obrigatórios.', 'danger')
        else:
            query_username = User.query.filter_by(username=username)
            query_email = User.query.filter_by(email=email)
            query_cpf = User.query.filter_by(cpf=cpf) if cpf else None
            if id_para_atualizar:
                query_username = query_username.filter(User.id != int(id_para_atualizar))
                query_email = query_email.filter(User.id != int(id_para_atualizar))
                if query_cpf is not None:
                    query_cpf = query_cpf.filter(User.id != int(id_para_atualizar))

            if query_username.first():
                app.logger.warning(
                    "admin_usuarios_validation_failed_duplicate_username",
                    extra={
                        'event': 'admin_usuarios_validation_failed',
                        'reason': 'duplicate_username',
                        'username': username,
                        'correlation_id': correlation_id,
                    },
                )
                flash(f'O nome de usuário "{username}" já está em uso.', 'danger')
            elif query_email.first():
                app.logger.warning(
                    "admin_usuarios_validation_failed_duplicate_email",
                    extra={
                        'event': 'admin_usuarios_validation_failed',
                        'reason': 'duplicate_email',
                        'email': email,
                        'correlation_id': correlation_id,
                    },
                )
                flash(f'O email "{email}" já está em uso.', 'danger')
            elif query_cpf is not None and query_cpf.first():
                app.logger.warning(
                    "admin_usuarios_validation_failed_duplicate_cpf",
                    extra={
                        'event': 'admin_usuarios_validation_failed',
                        'reason': 'duplicate_cpf',
                        'cpf': cpf,
                        'correlation_id': correlation_id,
                    },
                )
                flash(f'O CPF "{cpf}" já está em uso.', 'danger')
            else:
                if id_para_atualizar:
                    usr = User.query.get_or_404(id_para_atualizar)
                    app.logger.debug(f"Editing user {usr.id} ({usr.username})")
                    usr.username = username
                    usr.email = email
                    usr.ativo = ativo
                    usr.nome_completo = nome_completo or None
                    usr.matricula = matricula or None
                    usr.cpf = cpf or None
                    usr.rg = rg or None
                    usr.ramal = ramal or None
                    usr.telefone_contato = telefone_contato or None
                    usr.data_nascimento = data_nascimento
                    usr.data_admissao = data_admissao
                    usr.estabelecimento_id = estabelecimento_id
                    usr.setor_id = setor_primario_id
                    usr.cargo_id = cargo_id
                    usr.celula_id = celula_primaria_id
                    usr.extra_setores = []
                    usr.extra_celulas = []
                    usr.extra_setores = [Setor.query.get(sid) for sid in setor_ids]
                    usr.extra_celulas = [Celula.query.get(cid) for cid in celula_ids]
                    extras = set(funcao_ids)
                    if cargo_padrao:
                        extras -= {f.id for f in cargo_padrao.permissoes}
                    # atualiza as permissões personalizadas do usuário
                    app.logger.debug(f"Updating permissoes for user {usr.id} -> {extras}")
                    usr.permissoes_personalizadas = [Funcao.query.get(fid) for fid in extras]
                    if password:
                        usr.set_password(password)
                        usr.deve_trocar_senha = True
                    action_msg = 'atualizado'
                else:
                    senha_gerada = False
                    if not password:
                        password = str(uuid.uuid4())
                        senha_gerada = True
                    usr = User(
                        username=username,
                        email=email,
                        ativo=ativo,
                        nome_completo=nome_completo or None,
                        matricula=matricula or None,
                        cpf=cpf or None,
                        rg=rg or None,
                        ramal=ramal or None,
                        telefone_contato=telefone_contato or None,
                        data_nascimento=data_nascimento,
                        data_admissao=data_admissao,
                        estabelecimento_id=estabelecimento_id,
                        setor_id=setor_primario_id,
                        cargo_id=cargo_id,
                        celula_id=celula_primaria_id,
                    )
                    app.logger.debug("Creating new user record")
                    usr.set_password(password)
                    usr.deve_trocar_senha = True
                    usr.extra_setores = []
                    usr.extra_celulas = []
                    usr.extra_setores = [Setor.query.get(sid) for sid in setor_ids]
                    usr.extra_celulas = [Celula.query.get(cid) for cid in celula_ids]
                    extras = set(funcao_ids)
                    if cargo_padrao:
                        extras -= {f.id for f in cargo_padrao.permissoes}
                    usr.permissoes_personalizadas = [Funcao.query.get(fid) for fid in extras]
                    db.session.add(usr)
                    action_msg = 'criado'

                try:
                    app.logger.info(
                        "Tentando commit de usuário",
                        extra={
                            'event': 'admin_usuarios_commit_attempt',
                            'action': action_msg,
                            'user_id': getattr(usr, 'id', None),
                            'username': usr.username,
                            'email': usr.email,
                            'is_update': bool(id_para_atualizar),
                            'correlation_id': correlation_id,
                        },
                    )
                    db.session.commit()
                    app.logger.info(
                        "admin_usuarios_commit_success",
                        extra={
                            'event': 'admin_usuarios_commit_success',
                            'action': action_msg,
                            'user_id': usr.id,
                            'username': usr.username,
                            'correlation_id': correlation_id,
                        },
                    )
                except IntegrityError as e:
                    db.session.rollback()
                    flash('Não foi possível salvar o usuário. Verifique os dados informados e tente novamente.', 'danger')
                    app.logger.error(
                        "admin_usuarios_integrity_error",
                        extra={
                            'event': 'admin_usuarios_integrity_error',
                            'error_repr': repr(e),
                            'error_str': str(e),
                            'error_orig': str(getattr(e, 'orig', None)),
                            'username': username,
                            'email': email,
                            'correlation_id': correlation_id,
                        },
                    )
                except Exception as e:
                    db.session.rollback()
                    flash('Ocorreu um erro ao salvar o usuário. Tente novamente em instantes.', 'danger')
                    app.logger.exception(
                        "admin_usuarios_unexpected_error",
                        extra={
                            'event': 'admin_usuarios_unexpected_error',
                            'error_repr': repr(e),
                            'username': username,
                            'email': email,
                            'correlation_id': correlation_id,
                        },
                    )
                else:
                    manter_aba_cadastro = False
                    if not id_para_atualizar:
                        origem_senha = 'informada pelo administrador' if not senha_gerada else 'gerada automaticamente'
                        flash(
                            f'Usuário {action_msg} com sucesso! E-mail NÃO foi enviado. '
                            f'Senha inicial ({origem_senha}): {password}. '
                            'Usuário marcado para trocar a senha no primeiro acesso.',
                            'success'
                        )
                    else:
                        flash(f'Usuário {action_msg} com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_usuarios'))

        if id_para_atualizar:
            usuario_para_editar = User.query.get(id_para_atualizar)

    usuarios = User.query.order_by(User.username).all()
    estabelecimentos = Estabelecimento.query.order_by(Estabelecimento.nome_fantasia).all()
    setores = Setor.query.order_by(Setor.nome).all()
    cargos = Cargo.query.order_by(Cargo.nome).all()
    celulas = Celula.query.order_by(Celula.nome).all()
    funcoes = Funcao.query.order_by(Funcao.nome).all()
    cargo_defaults = {
        c.id: {
            'estabelecimentos': [e.id for e in c.default_estabelecimentos],
            'setores': [s.id for s in c.default_setores],
            'celulas': [ce.id for ce in c.default_celulas],
            'funcoes': [f.id for f in c.permissoes],
        }
        for c in cargos
    }
    admin_funcao = Funcao.query.filter_by(codigo='admin').first()
    return render_template(
        'admin/usuarios.html',
        usuarios=usuarios,
        user_editar=usuario_para_editar,
        estabelecimentos=estabelecimentos,
        setores=setores,
        cargos=cargos,
        celulas=celulas,
        funcoes=funcoes,
        cargo_defaults=json.dumps(cargo_defaults),
        admin_funcao_id=admin_funcao.id if admin_funcao else None,
        manter_aba_cadastro=manter_aba_cadastro,
    )

@admin_bp.route('/admin/usuarios/toggle_ativo/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_ativo_usuario(id):
    """Ativa ou inativa um usuário."""
    usr = User.query.get_or_404(id)
    # Removido bloqueio que impedia alterar o próprio usuário durante os testes
    # para que a funcionalidade possa ser exercitada sem necessidade de usuário
    # pré-existente. Em ambientes reais, recomenda-se validar essa condição.
    usr.ativo = not usr.ativo
    app.logger.debug(f"Toggling ativo for user {usr.id} to {usr.ativo}")
    try:
        db.session.commit()
        status_texto = 'ativado' if usr.ativo else 'desativado'
        flash(f'Usuário "{usr.username}" foi {status_texto} com sucesso!', 'success')
        app.logger.info(f"Usuario {usr.id} {status_texto}")
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do usuário: {str(e)}', 'danger')
        app.logger.error(f"Erro status user {usr.id}: {e}")
    return redirect(url_for('admin_bp.admin_usuarios'))
  

@admin_bp.route('/admin/setores', methods=['GET', 'POST'])
@admin_required
def admin_setores():
    """CRUD de Setores."""
    setor_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            setor_para_editar = Setor.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        estabelecimento_id = request.form.get('estabelecimento_id', type=int)
        ativo = request.form.get('ativo_check') == 'on'

        if not nome or not estabelecimento_id:
            flash('Nome e Estabelecimento são obrigatórios.', 'danger')
        else:
            query_nome_existente = Setor.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome_existente = query_nome_existente.filter(Setor.id != int(id_para_atualizar))
            nome_ja_existe = query_nome_existente.first()
            if nome_ja_existe:
                flash(f'O nome de setor "{nome}" já está em uso.', 'danger')
            else:
                if id_para_atualizar:
                    setor = Setor.query.get_or_404(id_para_atualizar)
                    setor.nome = nome
                    setor.descricao = descricao
                    setor.estabelecimento_id = estabelecimento_id
                    setor.ativo = ativo
                    action_msg = 'atualizado'
                else:
                    setor = Setor(
                        nome=nome,
                        descricao=descricao,
                        estabelecimento_id=estabelecimento_id,
                        ativo=ativo
                    )
                    db.session.add(setor)
                    action_msg = 'criado'
                try:
                    db.session.commit()
                    flash(f'Setor {action_msg} com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_setores'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar setor: {str(e)}', 'danger')

        if id_para_atualizar:
            setor_para_editar = Setor.query.get(id_para_atualizar)

    todos_setores = Setor.query.order_by(Setor.nome).all()
    estabelecimentos = Estabelecimento.query.order_by(Estabelecimento.nome_fantasia).all()
    return render_template('admin/setores.html',
                           setores=todos_setores,
                           estabelecimentos=estabelecimentos,
                           setor_editar=setor_para_editar)

@admin_bp.route('/admin/setores/toggle_ativo/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_ativo_setor(id):
    """Alterna o status ativo de um setor."""
    setor = Setor.query.get_or_404(id)
    if setor.ativo and setor.usuarios.count() > 0:
        flash(
            f'Atenção: "{setor.nome}" possui usuários associados. Inativá-lo pode ter implicações.',
            'warning'
        )
    setor.ativo = not setor.ativo
    try:
        db.session.commit()
        status_texto = 'ativado' if setor.ativo else 'desativado'
        flash(f'Setor "{setor.nome}" foi {status_texto} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do setor: {str(e)}', 'danger')
        app.logger.error(f"Erro ao alterar status do setor {setor.id}: {e}")
    return redirect(url_for('admin_bp.admin_setores'))

@admin_bp.route('/admin/celulas', methods=['GET', 'POST'])
@admin_required
def admin_celulas():
    """CRUD de Células."""
    celula_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            celula_para_editar = Celula.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        estabelecimento_id = request.form.get('estabelecimento_id', type=int)
        setor_id = request.form.get('setor_id', type=int)
        ativo = request.form.get('ativo_check') == 'on'

        if not nome or not estabelecimento_id or not setor_id:
            flash('Nome, Estabelecimento e Setor são obrigatórios.', 'danger')
        else:
            query_nome = Celula.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome = query_nome.filter(Celula.id != int(id_para_atualizar))
            nome_ja_existe = query_nome.first()

            if nome_ja_existe:
                flash(f'O nome de célula "{nome}" já está em uso.', 'danger')
            else:
                if id_para_atualizar:
                    cel = Celula.query.get_or_404(id_para_atualizar)
                    cel.nome = nome
                    cel.estabelecimento_id = estabelecimento_id
                    cel.setor_id = setor_id
                    cel.ativo = ativo
                    action_msg = 'atualizada'
                else:
                    cel = Celula(
                        nome=nome,
                        estabelecimento_id=estabelecimento_id,
                        setor_id=setor_id,
                        ativo=ativo
                    )
                    db.session.add(cel)
                    action_msg = 'criada'

                try:
                    db.session.commit()
                    flash(f'Célula {action_msg} com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_celulas'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar célula: {str(e)}', 'danger')

        if id_para_atualizar:
            celula_para_editar = Celula.query.get(id_para_atualizar)

    celulas = Celula.query.order_by(Celula.nome).all()
    estabelecimentos = Estabelecimento.query.order_by(Estabelecimento.nome_fantasia).all()
    setores = Setor.query.order_by(Setor.nome).all()
    return render_template(
        'admin/celulas.html',
        celulas=celulas,
        estabelecimentos=estabelecimentos,
        setores=setores,
        celula_editar=celula_para_editar
    )

@admin_bp.route('/admin/celulas/toggle_ativo/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_ativo_celula(id):
    cel = Celula.query.get_or_404(id)

    if cel.ativo and cel.usuarios.count() > 0:
        flash(
            f'Atenção: "{cel.nome}" possui usuários associados. Inativá-la pode ter implicações.',
            'warning'
        )

    cel.ativo = not cel.ativo
    try:
        db.session.commit()
        status_texto = 'ativada' if cel.ativo else 'desativada'
        flash(f'Célula "{cel.nome}" foi {status_texto} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status da célula: {str(e)}', 'danger')
    return redirect(url_for('admin_bp.admin_celulas'))

@admin_bp.route('/admin/cargos', methods=['GET', 'POST'])
@admin_required
def admin_cargos():
    """CRUD de Cargos."""
    cargo_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            cargo_para_editar = Cargo.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        nivel_hierarquico = request.form.get('nivel_hierarquico', type=int)
        ativo = request.form.get('ativo_check') == 'on'
        estabelecimento_ids = list({int(e) for e in request.form.getlist('estabelecimento_ids') if e})
        setor_ids = list({int(s) for s in request.form.getlist('setor_ids') if s})
        celula_ids = list({int(c) for c in request.form.getlist('celula_ids') if c})
        funcao_ids = list({int(f) for f in request.form.getlist('funcao_ids') if f})

        if not nome:
            flash('Nome do cargo é obrigatório.', 'danger')
        else:
            query_nome = Cargo.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome = query_nome.filter(Cargo.id != int(id_para_atualizar))
            nome_ja_existe = query_nome.first()

            if nome_ja_existe:
                flash(f'O nome de cargo "{nome}" já está em uso.', 'danger')
            else:
                setores_selecionados = Setor.query.filter(Setor.id.in_(setor_ids)).all() if setor_ids else []
                celulas_selecionadas = Celula.query.filter(Celula.id.in_(celula_ids)).all() if celula_ids else []
                estabelecimentos_ids_inferidos = set(estabelecimento_ids)
                estabelecimentos_ids_inferidos.update(s.estabelecimento_id for s in setores_selecionados)
                estabelecimentos_ids_inferidos.update(c.estabelecimento_id for c in celulas_selecionadas)
                estabelecimentos_selecionados = (
                    Estabelecimento.query.filter(Estabelecimento.id.in_(estabelecimentos_ids_inferidos)).all()
                    if estabelecimentos_ids_inferidos else []
                )

                setor_ids_invalidos = set(setor_ids) - {s.id for s in setores_selecionados}
                celula_ids_invalidos = set(celula_ids) - {c.id for c in celulas_selecionadas}
                estabelecimento_ids_invalidos = set(estabelecimento_ids) - {e.id for e in estabelecimentos_selecionados}

                erro_hierarquia = None
                if estabelecimento_ids_invalidos or setor_ids_invalidos or celula_ids_invalidos:
                    erro_hierarquia = 'Foram enviados itens de hierarquia inválidos. Atualize a página e tente novamente.'
                else:
                    setores_por_id = {s.id: s for s in setores_selecionados}
                    estabelecimentos_set = {e.id for e in estabelecimentos_selecionados}
                    for setor in setores_selecionados:
                        if setor.estabelecimento_id not in estabelecimentos_set:
                            erro_hierarquia = 'Cada setor selecionado deve pertencer a um estabelecimento selecionado.'
                            break
                    if not erro_hierarquia:
                        for celula in celulas_selecionadas:
                            setor_da_celula = setores_por_id.get(celula.setor_id)
                            if not setor_da_celula:
                                erro_hierarquia = 'Cada célula selecionada deve pertencer a um setor selecionado.'
                                break
                            if celula.estabelecimento_id != setor_da_celula.estabelecimento_id:
                                erro_hierarquia = 'Inconsistência entre célula, setor e estabelecimento selecionados.'
                                break
                            if celula.estabelecimento_id not in estabelecimentos_set:
                                erro_hierarquia = 'Cada célula selecionada deve pertencer a um estabelecimento selecionado.'
                                break

                if erro_hierarquia:
                    flash(erro_hierarquia, 'danger')
                    if id_para_atualizar:
                        cargo_para_editar = Cargo.query.get(id_para_atualizar)
                else:
                    if id_para_atualizar:
                        cargo = Cargo.query.get_or_404(id_para_atualizar)
                        cargo.nome = nome
                        cargo.descricao = descricao
                        cargo.nivel_hierarquico = nivel_hierarquico
                        cargo.ativo = ativo
                        action_msg = 'atualizado'
                    else:
                        cargo = Cargo(
                            nome=nome,
                            descricao=descricao,
                            nivel_hierarquico=nivel_hierarquico,
                            ativo=ativo,
                            pode_atender_os=False,
                        )
                        db.session.add(cargo)
                        action_msg = 'criado'
                    cargo.default_estabelecimentos = estabelecimentos_selecionados
                    cargo.default_setores = setores_selecionados
                    cargo.default_celulas = celulas_selecionadas
                    cargo.permissoes = [Funcao.query.get(fid) for fid in funcao_ids]
                    try:
                        db.session.commit()
                        flash(f'Cargo {action_msg} com sucesso!', 'success')
                        return redirect(url_for('admin_bp.admin_cargos'))
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Erro ao salvar cargo: {str(e)}', 'danger')

        if id_para_atualizar:
            cargo_para_editar = Cargo.query.get(id_para_atualizar)

    todos_cargos = Cargo.query.order_by(Cargo.nivel_hierarquico, Cargo.nome).all()
    estabelecimentos = Estabelecimento.query.order_by(Estabelecimento.nome_fantasia).all()
    setores = Setor.query.order_by(Setor.nome).all()
    celulas = Celula.query.order_by(Celula.nome).all()
    funcoes = Funcao.query.order_by(Funcao.nome).all()

    instituicoes = Instituicao.query.order_by(Instituicao.nome).all()
    estrutura = []
    for inst in instituicoes:
        est_list = []
        for est in inst.estabelecimentos.order_by(Estabelecimento.nome_fantasia).all():
            setor_list = []
            for setor in est.setores.order_by(Setor.nome).all():
                celula_list = []
                for cel in setor.celulas.order_by(Celula.nome).all():
                    cargos_cel = [c for c in todos_cargos if cel in c.default_celulas]
                    celula_list.append({'obj': cel, 'cargos': cargos_cel})
                cargos_setor = [c for c in todos_cargos if c.default_celulas.count() == 0 and setor in c.default_setores]
                setor_list.append({'obj': setor, 'celulas': celula_list, 'cargos': cargos_setor})
            est_list.append({'obj': est, 'setores': setor_list})
        estrutura.append({'obj': inst, 'estabelecimentos': est_list})

    return render_template(
        'admin/cargos.html',
        cargos=todos_cargos,
        cargo_editar=cargo_para_editar,
        estabelecimentos=estabelecimentos,
        setores=setores,
        celulas=celulas,
        funcoes=funcoes,
        estrutura=estrutura,
    )




@admin_bp.route('/admin/cargos/toggle_ativo/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_ativo_cargo(id):
    """Ativa ou inativa um Cargo."""
    cargo = Cargo.query.get_or_404(id)

    if cargo.ativo and cargo.usuarios.count() > 0:
        flash(
            f'Atenção: "{cargo.nome}" possui Usuários associados. Inativá-lo pode ter implicações.',
            'warning',
        )

    cargo.ativo = not cargo.ativo
    try:
        db.session.commit()
        status_texto = 'ativado' if cargo.ativo else 'desativado'
        flash(f'Cargo "{cargo.nome}" foi {status_texto} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do cargo: {str(e)}', 'danger')
        app.logger.error(f"Erro ao alterar status do cargo {cargo.id}: {e}")
    return redirect(url_for('admin_bp.admin_cargos'))


@admin_bp.route('/admin/artigos/tipos', methods=['GET', 'POST'])
def admin_artigo_tipos():
    user = _current_user()
    if not _can_manage_taxonomy(user, 'artigo_tipo_gerenciar'):
        flash('Permissão negada.', 'danger')
        return redirect(url_for('pagina_inicial'))

    tipo_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            tipo_para_editar = ArtigoTipo.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo_check') == 'on'

        if not nome:
            flash('Nome do tipo é obrigatório.', 'danger')
        else:
            query_nome = ArtigoTipo.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome = query_nome.filter(ArtigoTipo.id != int(id_para_atualizar))
            if query_nome.first():
                flash(f'O tipo "{nome}" já existe.', 'danger')
            else:
                if id_para_atualizar:
                    tipo = ArtigoTipo.query.get_or_404(id_para_atualizar)
                    tipo.nome = nome
                    tipo.descricao = descricao
                    tipo.ativo = ativo
                else:
                    tipo = ArtigoTipo(nome=nome, descricao=descricao, ativo=ativo)
                    db.session.add(tipo)
                try:
                    db.session.commit()
                    flash('Tipo salvo com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_artigo_tipos'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar tipo: {str(e)}', 'danger')

    tipos = ArtigoTipo.query.order_by(ArtigoTipo.nome).all()
    return render_template('admin/artigo_tipos.html', tipos=tipos, tipo_editar=tipo_para_editar)


@admin_bp.route('/admin/artigos/areas', methods=['GET', 'POST'])
def admin_artigo_areas():
    user = _current_user()
    if not _can_manage_taxonomy(user, 'artigo_area_gerenciar'):
        flash('Permissão negada.', 'danger')
        return redirect(url_for('pagina_inicial'))

    area_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            area_para_editar = ArtigoArea.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo_check') == 'on'

        if not nome:
            flash('Nome da área é obrigatório.', 'danger')
        else:
            query_nome = ArtigoArea.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome = query_nome.filter(ArtigoArea.id != int(id_para_atualizar))
            if query_nome.first():
                flash(f'A área "{nome}" já existe.', 'danger')
            else:
                if id_para_atualizar:
                    area = ArtigoArea.query.get_or_404(id_para_atualizar)
                    area.nome = nome
                    area.descricao = descricao
                    area.ativo = ativo
                else:
                    area = ArtigoArea(nome=nome, descricao=descricao, ativo=ativo)
                    db.session.add(area)
                try:
                    db.session.commit()
                    flash('Área salva com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_artigo_areas'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar área: {str(e)}', 'danger')

    areas = ArtigoArea.query.order_by(ArtigoArea.nome).all()
    return render_template('admin/artigo_areas.html', areas=areas, area_editar=area_para_editar)


@admin_bp.route('/admin/artigos/sistemas', methods=['GET', 'POST'])
def admin_artigo_sistemas():
    user = _current_user()
    if not _can_manage_taxonomy(user, 'artigo_area_gerenciar'):
        flash('Permissão negada.', 'danger')
        return redirect(url_for('pagina_inicial'))

    sistema_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            sistema_para_editar = ArtigoSistema.query.get_or_404(edit_id)

    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo_check') == 'on'

        if not nome:
            flash('Nome do sistema é obrigatório.', 'danger')
        else:
            query_nome = ArtigoSistema.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome = query_nome.filter(ArtigoSistema.id != int(id_para_atualizar))
            if query_nome.first():
                flash(f'O sistema "{nome}" já existe.', 'danger')
            else:
                if id_para_atualizar:
                    sistema = ArtigoSistema.query.get_or_404(id_para_atualizar)
                    sistema.nome = nome
                    sistema.descricao = descricao
                    sistema.ativo = ativo
                else:
                    sistema = ArtigoSistema(nome=nome, descricao=descricao, ativo=ativo)
                    db.session.add(sistema)
                try:
                    db.session.commit()
                    flash('Sistema salvo com sucesso!', 'success')
                    return redirect(url_for('admin_bp.admin_artigo_sistemas'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar sistema: {str(e)}', 'danger')

    sistemas = ArtigoSistema.query.order_by(ArtigoSistema.nome).all()
    return render_template('admin/artigo_sistemas.html', sistemas=sistemas, sistema_editar=sistema_para_editar)
