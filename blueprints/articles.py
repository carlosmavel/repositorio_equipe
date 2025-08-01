from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app as app
from sqlalchemy import or_, func

try:
    from ..database import db
except ImportError:
    from database import db

try:
    from ..models import Article, Attachment, Comment, Notification, User, RevisionRequest
except ImportError:
    from models import Article, Attachment, Comment, Notification, User, RevisionRequest

try:
    from ..enums import ArticleStatus, ArticleVisibility, Permissao
except ImportError:
    from enums import ArticleStatus, ArticleVisibility, Permissao

try:
    from ..utils import (
        sanitize_html,
        extract_text,
        eligible_review_notification_users,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (
        sanitize_html,
        extract_text,
        eligible_review_notification_users,
        user_can_view_article,
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
    )
import time
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from mimetypes import guess_type
from werkzeug.utils import secure_filename
import os
import json
import uuid

articles_bp = Blueprint('articles_bp', __name__)
@articles_bp.route('/novo-artigo', methods=['GET', 'POST'], endpoint='novo_artigo')
def novo_artigo():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not (user.has_permissao('admin') or user.has_permissao('artigo_criar')):
        flash('Permissão negada.', 'danger')
        return redirect(url_for('meus_artigos'))

    # Processa envio do formulário de criação de artigo
    if request.method == 'POST':
      
        # 1) Coleta dados do formulário
        titulo      = request.form['titulo'].strip()
        texto_raw   = request.form['texto']
        texto_limpo = sanitize_html(texto_raw)
        files       = request.files.getlist('files')

        # 1.1) Descobre se é rascunho ou envio para revisão
        acao   = request.form.get('acao', 'enviar')  # 'rascunho' ou 'enviar'
        status = (ArticleStatus.RASCUNHO
                  if acao == 'rascunho'
                  else ArticleStatus.PENDENTE)

        user = User.query.filter_by(username=session['username']).first()

        # 2) Define visibilidade e contextos
        vis_str = (request.form.get('visibility') or 'celula').split(',')[0]
        vis = ArticleVisibility.CELULA
        if vis_str in ArticleVisibility._value2member_map_:
            vis = ArticleVisibility(vis_str)

        inst_id = est_id = setor_vis_id = vis_cel_id = None
        if vis is ArticleVisibility.INSTITUICAO and user.estabelecimento:
            inst_id = user.estabelecimento.instituicao_id
        elif vis is ArticleVisibility.ESTABELECIMENTO:
            est_id = user.estabelecimento_id
        elif vis is ArticleVisibility.SETOR:
            setor_vis_id = user.setor_id
        elif vis is ArticleVisibility.CELULA:
            vis_cel_id = user.celula_id

        # 3) Cria o artigo (sem arquivos ainda) e dá um flush para ter ID
        artigo = Article(
            titulo     = titulo,
            texto      = texto_limpo,
            status     = status,
            user_id    = user.id,
            celula_id  = user.celula_id or 1,
            visibility = vis,
            instituicao_id = inst_id,
            estabelecimento_id = est_id,
            setor_id = setor_vis_id,
            vis_celula_id = vis_cel_id,
            arquivos   = None,
            created_at = datetime.now(timezone.utc),
            updated_at = datetime.now(timezone.utc)
        )
        db.session.add(artigo)
        db.session.flush()

        # 3) Salva arquivos com nome único, extrai texto e cria Attachments
        filenames = []
        for f in files:
            if f and f.filename:
                original = secure_filename(f.filename)
                if len(original) > 40:
                    name, ext = os.path.splitext(original)
                    original = name[:40 - len(ext)] + ext
                unique_name = f"{uuid.uuid4().hex}_{original}"
                dest       = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                f.save(dest)
                filenames.append(unique_name)

                # extrai texto e descobre MIME
                texto_extraido = extract_text(dest)
                mime_type, _   = guess_type(dest)

                # cria o registro de attachment
                attachment = Attachment(
                    article   = artigo,
                    filename  = unique_name,
                    mime_type = mime_type or 'application/octet-stream',
                    content   = texto_extraido
                )
                db.session.add(attachment)

        # 4) Atualiza o campo JSON de nomes no artigo
        artigo.arquivos = json.dumps(filenames) if filenames else None

        # 5) Persiste tudo num único commit
        db.session.commit()

        # 6) Notifica responsáveis/admins, se necessário
        if status is ArticleStatus.PENDENTE:
            destinatarios = eligible_review_notification_users(artigo)
            for dest in destinatarios:
                notif = Notification(
                    user_id = dest.id,
                    message = f'Novo artigo pendente para revisão: “{artigo.titulo}”',
                    url     = url_for('aprovacao_detail', artigo_id=artigo.id)
                )
                db.session.add(notif)
            db.session.commit()

        # 7) Feedback para o usuário
        flash(
            'Rascunho salvo!' if status is ArticleStatus.RASCUNHO
            else 'Artigo criado e enviado para revisão!',
            'success'
        )
        time.sleep(1)
        return redirect(url_for('meus_artigos'))

    # GET → exibe formulário
    return render_template('artigos/novo_artigo.html')

@articles_bp.route('/meus-artigos', endpoint='meus_artigos')
def meus_artigos():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first_or_404()
    artigos = (Article.query
                .filter_by(user_id=user.id)
                .order_by(Article.created_at.desc())
                .all())
    for art in artigos:
        dt = art.created_at or datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        art.local_created = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        dt2 = art.updated_at or dt
        if dt2.tzinfo is None:
            dt2 = dt2.replace(tzinfo=timezone.utc)
        art.local_updated = dt2.astimezone(ZoneInfo("America/Sao_Paulo"))
    return render_template(
        'artigos/meus_artigos.html',
        artigos=artigos,
        now=datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

@articles_bp.route('/artigo/<int:artigo_id>', methods=['GET','POST'], endpoint='artigo')
def artigo(artigo_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    artigo = Article.query.get_or_404(artigo_id)
    user = User.query.filter_by(username=session['username']).first()
    if not user_can_view_article(user, artigo):
        flash('Você não tem permissão para ver este artigo.', 'danger')
        return redirect(url_for('pagina_inicial'))

    if request.method == 'POST':
        if not user_can_edit_article(user, artigo):
            flash('Permissão negada.', 'danger')
            return redirect(url_for('artigo', artigo_id=artigo_id))
        # 1) campos básicos
        artigo.titulo = request.form['titulo']
        artigo.texto  = request.form['texto']
        artigo.status = ArticleStatus.PENDENTE
        artigo.updated_at = datetime.now(timezone.utc)

        # 2) arquivos existentes
        existing = json.loads(artigo.arquivos or '[]')

        # 2.1) exclusões marcadas
        deletados = request.form.getlist('delete_files')
        if deletados:
            for fname in deletados:
                if fname in existing:
                    existing.remove(fname)
                    # remove do disco
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    except FileNotFoundError:
                        pass

        # 2.2) novos uploads
        files = request.files.getlist('files')
        for f in files:
            if f and f.filename:
                original = secure_filename(f.filename)
                if len(original) > 40:
                    name, ext = os.path.splitext(original)
                    original = name[:40 - len(ext)] + ext
                dest = os.path.join(app.config['UPLOAD_FOLDER'], original)
                f.save(dest)
                existing.append(original)

        artigo.arquivos = json.dumps(existing) if existing else None

        db.session.commit()
        flash('Artigo enviado para revisão!', 'success')
        return redirect(url_for('meus_artigos'))

    arquivos = json.loads(artigo.arquivos or '[]')
    return render_template('artigos/artigo.html', artigo=artigo, arquivos=arquivos)

@articles_bp.route("/artigo/<int:artigo_id>/editar", methods=["GET", "POST"], endpoint='editar_artigo')
def editar_artigo(artigo_id):
    if "username" not in session:
        return redirect(url_for("login"))

    artigo = Article.query.get_or_404(artigo_id)

    user = User.query.get(session['user_id'])
    if not user_can_edit_article(user, artigo):
        flash("Você não tem permissão para editar este artigo.", "danger")
        return redirect(url_for("artigo", artigo_id=artigo_id))

    if request.method == "POST":
        acao = request.form.get("acao", "salvar")   # salvar | enviar

        # campos básicos
        artigo.titulo = request.form["titulo"]
        artigo.texto  = request.form["texto"]
        artigo.updated_at = datetime.now(timezone.utc)

        # visibilidade
        user = User.query.filter_by(username=session["username"]).first()
        vis_str = (request.form.get("visibility") or artigo.visibility.value).split(',')[0]
        vis = ArticleVisibility.CELULA
        if vis_str in ArticleVisibility._value2member_map_:
            vis = ArticleVisibility(vis_str)

        inst_id = est_id = setor_vis_id = vis_cel_id = None
        if vis is ArticleVisibility.INSTITUICAO and user.estabelecimento:
            inst_id = user.estabelecimento.instituicao_id
        elif vis is ArticleVisibility.ESTABELECIMENTO:
            est_id = user.estabelecimento_id
        elif vis is ArticleVisibility.SETOR:
            setor_vis_id = user.setor_id
        elif vis is ArticleVisibility.CELULA:
            vis_cel_id = user.celula_id

        artigo.visibility = vis
        artigo.instituicao_id = inst_id
        artigo.estabelecimento_id = est_id
        artigo.setor_id = setor_vis_id
        artigo.vis_celula_id = vis_cel_id

        # anexos ─ exclusões + novos
        existing = json.loads(artigo.arquivos or "[]")

        # exclusões
        for fname in request.form.getlist("delete_files"):
            if fname in existing:
                existing.remove(fname)

                # Encontrar e deletar o Attachment correspondente no banco
                attachment_to_delete = Attachment.query.filter_by(article_id=artigo.id, filename=fname).first()
                if attachment_to_delete:
                    db.session.delete(attachment_to_delete)  # Deleta o objeto Attachment da sessão
                try:
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                except FileNotFoundError:
                    pass

        # novos uploads
        for f in request.files.getlist("files"):
            if f and f.filename:
                original = secure_filename(f.filename)
                if len(original) > 40:
                    name, ext = os.path.splitext(original)
                    original = name[:40 - len(ext)] + ext
                unique_name = f"{uuid.uuid4().hex}_{original}"
                dest = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                f.save(dest)
                existing.append(unique_name)

                # 1) extrai texto
                texto_extraido = extract_text(dest)
                # 2) descobre o MIME
                mime_type, _ = guess_type(dest)
                # 3) adiciona o attachment ao session
                attachment = Attachment(
                    article=artigo,
                    filename=unique_name,
                    mime_type=mime_type or "application/octet-stream",
                    content=texto_extraido
                )
                db.session.add(attachment)

        artigo.arquivos = json.dumps(existing) if existing else None

        # se usuário clicou “Enviar para revisão”
        if acao == "enviar":
            artigo.status = ArticleStatus.PENDENTE
            # 🔔 notifica responsáveis / admins
            destinatarios = eligible_review_notification_users(artigo)
            for dest in destinatarios:
                n = Notification(
                    user_id = dest.id,
                    message = f"Novo artigo pendente para revisão: “{artigo.titulo}”",
                    url     = url_for('aprovacao_detail', artigo_id=artigo.id)
                )
                db.session.add(n)
            flash("Artigo enviado para revisão!", "success")
        else:
            flash("Artigo salvo!", "success")

        db.session.commit()
        return redirect(url_for("artigo", artigo_id=artigo.id))

    # GET
    arquivos = json.loads(artigo.arquivos or "[]")
    return render_template("artigos/editar_artigo.html", artigo=artigo, arquivos=arquivos)

@articles_bp.route("/aprovacao", endpoint='aprovacao')
def aprovacao():
    if "user_id" not in session:
        flash("Por favor, faça login para acessar esta página.", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    rev_apr_perms = [
        Permissao.ARTIGO_APROVAR_CELULA,
        Permissao.ARTIGO_APROVAR_SETOR,
        Permissao.ARTIGO_APROVAR_ESTABELECIMENTO,
        Permissao.ARTIGO_APROVAR_INSTITUICAO,
        Permissao.ARTIGO_APROVAR_TODAS,
        Permissao.ARTIGO_REVISAR_CELULA,
        Permissao.ARTIGO_REVISAR_SETOR,
        Permissao.ARTIGO_REVISAR_ESTABELECIMENTO,
        Permissao.ARTIGO_REVISAR_INSTITUICAO,
        Permissao.ARTIGO_REVISAR_TODAS,
    ]
    if not user or not (
        user.has_permissao("admin")
        or any(user.has_permissao(p.value) for p in rev_apr_perms)
    ):
        flash("Permissão negada.", "danger")
        return redirect(url_for("login"))

    pendentes_query = Article.query.filter_by(status=ArticleStatus.PENDENTE)
    pendentes = [
        a for a in pendentes_query.order_by(Article.created_at.asc()).all()
        if user_can_approve_article(user, a) or user_can_review_article(user, a)
    ]

    uid = user.id
    revisados_query = (
        Article.query
        .join(Comment, Comment.artigo_id == Article.id)
        .filter(Comment.user_id == uid)
        .filter(Article.status != ArticleStatus.PENDENTE)
    )
    revisados = [
        a for a in (
            revisados_query
            .group_by(Article.id)
            .order_by(func.max(Comment.created_at).desc())
            .all()
        )
        if user_can_approve_article(user, a) or user_can_review_article(user, a)
    ]

    for lista in (pendentes, revisados):
        for art in lista:
            dt_created = art.created_at or datetime.now(timezone.utc)
            if dt_created.tzinfo is None:
                dt_created = dt_created.replace(tzinfo=timezone.utc)
            art.local_created = dt_created.astimezone(ZoneInfo("America/Sao_Paulo"))

            dt_updated = art.updated_at or dt_created
            if dt_updated.tzinfo is None:
                dt_updated = dt_updated.replace(tzinfo=timezone.utc)
            art.local_updated = dt_updated.astimezone(ZoneInfo("America/Sao_Paulo"))

    return render_template(
        "artigos/aprovacao.html",
        pendentes=pendentes,
        revisados=revisados
    )

@articles_bp.route('/aprovacao/<int:artigo_id>', methods=['GET', 'POST'], endpoint='aprovacao_detail')
def aprovacao_detail(artigo_id):
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar esta página.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    rev_apr_perms = [
        Permissao.ARTIGO_APROVAR_CELULA,
        Permissao.ARTIGO_APROVAR_SETOR,
        Permissao.ARTIGO_APROVAR_ESTABELECIMENTO,
        Permissao.ARTIGO_APROVAR_INSTITUICAO,
        Permissao.ARTIGO_APROVAR_TODAS,
        Permissao.ARTIGO_REVISAR_CELULA,
        Permissao.ARTIGO_REVISAR_SETOR,
        Permissao.ARTIGO_REVISAR_ESTABELECIMENTO,
        Permissao.ARTIGO_REVISAR_INSTITUICAO,
        Permissao.ARTIGO_REVISAR_TODAS,
    ]
    if not user or not (
        user.has_permissao('admin')
        or any(user.has_permissao(p.value) for p in rev_apr_perms)
    ):
        flash('Permissão negada.', 'danger')
        return redirect(url_for('login'))

    artigo = Article.query.get_or_404(artigo_id)
    if not (
        user_can_approve_article(user, artigo) or
        user_can_review_article(user, artigo)
    ):
        flash("Permissão negada.", "danger")
        return redirect(url_for("aprovacao"))

    if request.method=='POST':
        acao       = request.form['acao']                 # aprovar / ajustar / rejeitar
        comentario = request.form.get('comentario','').strip()

        # 1) Atualiza o status -------------------------------------------------
        if acao == 'aprovar':
            if not user_can_approve_article(user, artigo):
                flash('Permissão negada.', 'danger')
                return redirect(url_for('aprovacao_detail', artigo_id=artigo_id))
            artigo.status = ArticleStatus.APROVADO
            msg = f"Artigo '{artigo.titulo}' aprovado!"
        elif acao == 'ajustar':
            if not user_can_review_article(user, artigo):
                flash('Permissão negada.', 'danger')
                return redirect(url_for('aprovacao_detail', artigo_id=artigo_id))
            artigo.status = ArticleStatus.EM_AJUSTE
            msg = f"Artigo '{artigo.titulo}' marcado como Em Ajuste."
        elif acao == 'rejeitar':
            if not user_can_review_article(user, artigo):
                flash('Permissão negada.', 'danger')
                return redirect(url_for('aprovacao_detail', artigo_id=artigo_id))
            artigo.status = ArticleStatus.REJEITADO
            msg = f"Artigo '{artigo.titulo}' rejeitado!"
        else:
            flash('Ação desconhecida.', 'warning')
            return redirect(url_for('aprovacao_detail', artigo_id=artigo_id))

        # 2) Registra comentário de ajuste/aprovação/rejeição ------------------
        novo_comment = Comment(
            artigo_id = artigo.id,
            user_id   = user.id,
            texto     = comentario or f"(Mudança de status para {acao})"
        )
        db.session.add(novo_comment)
        db.session.commit()

        # 3) Notifica autor com o status correto ------------------------------
        notif = Notification(
            user_id = artigo.user_id,
            message = f"Seu artigo “{artigo.titulo}” foi {artigo.status.value.replace('_',' ')}",
            url     = url_for('artigo', artigo_id=artigo.id)
        )
        db.session.add(notif)
        db.session.commit()

        # 4) Mensagem de confirmação e redirecionamento -----------------------
        flash(msg, 'success')
        return redirect(url_for('aprovacao'))

    # GET → renderiza detalhes e histórico
    arquivos = json.loads(artigo.arquivos or '[]')
    return render_template(
        'artigos/aprovacao_detail.html',
        artigo   = artigo,
        arquivos = arquivos
    )

@articles_bp.route('/solicitar_revisao/<int:artigo_id>', methods=['GET','POST'], endpoint='solicitar_revisao')
def solicitar_revisao(artigo_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    artigo = Article.query.get_or_404(artigo_id)
    user    = User.query.filter_by(username=session['username']).first()

    if request.method=='POST':
        comentario = request.form.get('comentario','').strip()
        if not comentario:
            flash('Insira um comentário.', 'warning')
            return redirect(url_for('solicitar_revisao', artigo_id=artigo.id))

        rr = RevisionRequest(
            artigo_id=artigo.id,
            user_id=user.id,
            comentario=comentario
        )
        db.session.add(rr)

        artigo.status = ArticleStatus.EM_REVISAO
        db.session.commit()

        destinatarios = [artigo.author] + [u for u in User.query.all() if u.has_permissao('admin')]
        for u in destinatarios:
            n = Notification(
                user_id=u.id,
                message=f"{user.username} solicitou revisão de “{artigo.titulo}”",
                url=url_for('artigo', artigo_id=artigo.id)
            )
            db.session.add(n)
        db.session.commit()

        flash('Pedido de revisão enviado!', 'success')
        return redirect(url_for('artigo', artigo_id=artigo.id))

    return render_template('artigos/solicitar_revisao.html', artigo=artigo)

@articles_bp.route('/pesquisar', endpoint='pesquisar')
def pesquisar():
    if 'username' not in session:
        return redirect(url_for('login'))

    q = request.args.get('q','').strip()
    query = Article.query.filter_by(status=ArticleStatus.APROVADO)

    if q:
        exact = False
        term = q
        if len(term) >= 2 and term.startswith('"') and term.endswith('"'):
            term = term[1:-1]
            exact = True

        tokens = [term] if exact else [t for t in term.split() if t]

        for token in tokens:
            like = f"%{token}%"
            sub = (
                db.session.query(Attachment.article_id)
                .filter(
                    or_(
                        Attachment.filename.ilike(like),
                        Attachment.content.ilike(like)
                    )
                )
                .scalar_subquery()
            )

            query = query.filter(
                or_(
                    Article.titulo.ilike(like),
                    Article.texto.ilike(like),
                    Article.id.in_(sub)
                )
            )

    artigos = query.order_by(Article.created_at.desc()).all()

    # Filtra conforme visibilidade
    user = User.query.filter_by(username=session['username']).first()
    artigos = [a for a in artigos if user_can_view_article(user, a)]

    # formata datas para o fuso local
    for art in artigos:
        dt = art.created_at or datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        art.local_created = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        dt2 = art.updated_at or dt
        if dt2.tzinfo is None:
            dt2 = dt2.replace(tzinfo=timezone.utc)
        art.local_aprovado = dt2.astimezone(ZoneInfo("America/Sao_Paulo"))

    return render_template(
        'artigos/pesquisar.html',
        artigos=artigos,
        q=q,
        now=datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

