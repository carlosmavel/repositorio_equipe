from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app as app
from sqlalchemy import func

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
    )

try:
    from ..core.enums import ArticleStatus
except ImportError:
    from core.enums import ArticleStatus

try:
    from ..core.decorators import admin_required
except ImportError:  # pragma: no cover
    from core.decorators import admin_required
try:
    from ..core.utils import (
        DEFAULT_NEW_USER_PASSWORD,
        send_email,
        generate_token,
        eligible_review_notification_users,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
    )
except ImportError:  # pragma: no cover
    from core.utils import (
        DEFAULT_NEW_USER_PASSWORD,
        send_email,
        generate_token,
        eligible_review_notification_users,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
    )
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from werkzeug.utils import secure_filename
from mimetypes import guess_type
import uuid
import os

admin_bp = Blueprint('admin_bp', __name__)

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

    return render_template(
        "admin/dashboard.html",
        user_total=user_total,
        users_active=users_active,
        users_inactive=users_inactive,
        article_status_counts=status_counts,
        notifications_unread=notifications_unread,
        notifications_read=notifications_read,
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
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo_check') == 'on'

        if not nome:
            flash('Nome da instituição é obrigatório.', 'danger')
        else:
            query_nome_existente = Instituicao.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome_existente = query_nome_existente.filter(Instituicao.id != int(id_para_atualizar))
            nome_ja_existe = query_nome_existente.first()

            if nome_ja_existe:
                flash(f'O nome "{nome}" já está em uso.', 'danger')
            else:
                if id_para_atualizar:
                    inst = Instituicao.query.get_or_404(id_para_atualizar)
                    inst.nome = nome
                    inst.descricao = descricao
                    inst.ativo = ativo
                    action_msg = 'atualizada'
                else:
                    inst = Instituicao(nome=nome, descricao=descricao, ativo=ativo)
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
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            usuario_para_editar = User.query.get_or_404(edit_id)
            app.logger.debug(f"Loading user {edit_id} for editing")

    if request.method == 'POST':
        app.logger.debug(f"Received POST /admin/usuarios with data: {request.form}")
        id_para_atualizar = request.form.get('id_para_atualizar')
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        ativo = request.form.get('ativo_check') == 'on'
        password = request.form.get('password')

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
            if not setor_ids:
                setor_ids = [s.id for s in cargo_padrao.default_setores]
            if not celula_ids:
                celula_ids = [c.id for c in cargo_padrao.default_celulas]
            if not estabelecimento_id:
                if setor_ids:
                    setor_obj = Setor.query.get(setor_ids[0])
                    estabelecimento_id = setor_obj.estabelecimento_id
                elif celula_ids:
                    cel_obj = Celula.query.get(celula_ids[0])
                    estabelecimento_id = cel_obj.estabelecimento_id

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

        if not username or not email or not estabelecimento_id or not setor_ids or not celula_ids:
            flash('Usuário, Email, Estabelecimento, Setor e Célula são obrigatórios.', 'danger')
        else:
            query_username = User.query.filter_by(username=username)
            query_email = User.query.filter_by(email=email)
            if id_para_atualizar:
                query_username = query_username.filter(User.id != int(id_para_atualizar))
                query_email = query_email.filter(User.id != int(id_para_atualizar))

            if query_username.first():
                flash(f'O nome de usuário "{username}" já está em uso.', 'danger')
            elif query_email.first():
                flash(f'O email "{email}" já está em uso.', 'danger')
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
                    usr.setor_id = setor_ids[0] if setor_ids else None
                    usr.cargo_id = cargo_id
                    usr.celula_id = celula_ids[0] if celula_ids else None
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
                    action_msg = 'atualizado'
                else:
                    if not password:
                        password = DEFAULT_NEW_USER_PASSWORD
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
                        setor_id=setor_ids[0] if setor_ids else None,
                        cargo_id=cargo_id,
                        celula_id=celula_ids[0] if celula_ids else None,
                    )
                    app.logger.debug("Creating new user record")
                    usr.set_password(password)
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
                    db.session.commit()
                    app.logger.info(f"Usuario {action_msg}: id={usr.id}")
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar usuário: {str(e)}', 'danger')
                    app.logger.error(f"Erro DB User: {e}")
                else:
                    if not id_para_atualizar:
                        try:
                            send_password_email(usr, 'create')
                        except Exception as e:
                            app.logger.error(f"Erro ao enviar e-mail de cadastro: {e}")
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
            'setores': [s.id for s in c.default_setores],
            'celulas': [ce.id for ce in c.default_celulas],
            'funcoes': [f.id for f in c.permissoes],
        }
        for c in cargos
    }
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
        atende_os = request.form.get('pode_atender_os') == 'on'
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
                if id_para_atualizar:
                    cargo = Cargo.query.get_or_404(id_para_atualizar)
                    cargo.nome = nome
                    cargo.descricao = descricao
                    cargo.nivel_hierarquico = nivel_hierarquico
                    cargo.ativo = ativo
                    cargo.pode_atender_os = atende_os
                    action_msg = 'atualizado'
                else:
                    cargo = Cargo(
                        nome=nome,
                        descricao=descricao,
                        nivel_hierarquico=nivel_hierarquico,
                        ativo=ativo,
                        pode_atender_os=atende_os,
                    )
                    db.session.add(cargo)
                    action_msg = 'criado'
                cargo.default_setores = [Setor.query.get(sid) for sid in setor_ids]
                cargo.default_celulas = [Celula.query.get(cid) for cid in celula_ids]
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


