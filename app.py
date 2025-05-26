import os
import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import (
    Flask, request, render_template, redirect, url_for,
    session, send_from_directory, flash
)
from flask_migrate import Migrate
from werkzeug.security import check_password_hash         # ← 1) IMPORTADO
from sqlalchemy import or_, func

from database import db
from enums import ArticleStatus
from models import User, Article, RevisionRequest, Notification, Comment
from utils import sanitize_html

# -------------------------------------------------------------------------
# Configuração da Aplicação
# -------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave_de_desenvolvimento')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI',
    'postgresql://appuser:AppUser2025%21@localhost:5432/repositorio_equipe_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# pastas de upload
UPLOAD_FOLDER = 'uploads'
PROFILE_PICS_FOLDER = 'profile_pics'
for folder in (UPLOAD_FOLDER, PROFILE_PICS_FOLDER):
    os.makedirs(folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER

# -------------------------------------------------------------------------
# Context Processors
# -------------------------------------------------------------------------
@app.context_processor
def inject_notificacoes():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            notifs = (Notification.query
                      .filter_by(user_id=user.id, lido=False)
                      .order_by(Notification.created_at.desc())
                      .limit(10)
                      .all())
            return {
                'notificacoes': len(notifs),
                'notificacoes_list': notifs
            }
    return {'notificacoes': 0, 'notificacoes_list': []}

@app.context_processor
def inject_enums():
    return dict(ArticleStatus=ArticleStatus)

@app.context_processor
def inject_current_user():
    if 'username' in session:
        return {'current_user': User.query.filter_by(username=session['username']).first()}
    return {'current_user': None}

@app.context_processor
def inject_zoneinfo():
    # torna ZoneInfo disponível em {{ }}
    return dict(ZoneInfo=ZoneInfo)

# -------------------------------------------------------------------------
# Rotas
# -------------------------------------------------------------------------
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('pesquisar'))
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    # para o JS de pré-visualização de fotos
    users_json = {
        u.username: {"foto": u.foto or ""} for u in User.query.all()
    }

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            # -------- credenciais corretas ----------
            session["user_id"] = user.id
            session["username"] = user.username          # ← 2) salvo username
            session["role"] = user.role                  # ← 3) salvo role
            return redirect(url_for("pesquisar"))

        # -------- credenciais inválidas -------------
        flash("Usuário ou senha inválidos!", "danger")
        return render_template("login.html", users_json=users_json)

    # GET → exibe formulário limpo
    return render_template("login.html", users_json=users_json)

@app.route('/novo-artigo', methods=['GET', 'POST'])
def novo_artigo():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Só colaboradores, editores e admins podem criar
    if request.method == 'POST' and session['role'] in ['colaborador', 'editor', 'admin']:
        from models import User, Article, Notification

        # 1) Coleta dados do formulário
        titulo      = request.form['titulo'].strip()
        texto_raw   = request.form['texto']
        texto_limpo = sanitize_html(texto_raw)   # ← sanitização aqui
        files       = request.files.getlist('files')

        # 1.1) Descobre se é rascunho ou envio para revisão
        acao   = request.form.get('acao', 'enviar')  # 'rascunho' ou 'enviar'
        status = (ArticleStatus.RASCUNHO
                  if acao == 'rascunho'
                  else ArticleStatus.PENDENTE)

        # 2) Salva arquivos e monta lista de nomes
        filenames = []
        for f in files:
            if f and f.filename:
                dest = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
                f.save(dest)
                filenames.append(f.filename)

        # 3) Cria o artigo no banco com texto sanitizado
        user = User.query.filter_by(username=session['username']).first()
        artigo = Article(
            titulo     = titulo,
            texto      = texto_limpo,
            status     = status,
            user_id    = user.id,
            arquivos   = json.dumps(filenames) if filenames else None,
            created_at = datetime.now(timezone.utc),
            updated_at = datetime.now(timezone.utc)
        )
        db.session.add(artigo)
        db.session.commit()

        # 4) Se não for rascunho, notifica editores/admins
        if status is ArticleStatus.PENDENTE:
            destinatarios = User.query.filter(
                User.role.in_(['editor', 'admin'])
            ).all()
            for dest in destinatarios:
                notif = Notification(
                    user_id = dest.id,
                    message = f'Novo artigo pendente para revisão: “{artigo.titulo}”',
                    url     = url_for('aprovacao_detail', artigo_id=artigo.id)
                )
                db.session.add(notif)
            db.session.commit()

        flash(
            'Rascunho salvo!' if status is ArticleStatus.RASCUNHO
            else 'Artigo criado e enviado para revisão!',
            'success'
        )
        time.sleep(1)
        return redirect(url_for('meus_artigos'))

    # GET → exibe formulário
    return render_template('novo_artigo.html')

@app.route('/meus-artigos')
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
    return render_template(
        'meus_artigos.html',
        artigos=artigos,
        now=datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

@app.route('/artigo/<int:artigo_id>', methods=['GET','POST'])
def artigo(artigo_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    artigo = Article.query.get_or_404(artigo_id)

    if request.method == 'POST':
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
                dest = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
                f.save(dest)
                existing.append(f.filename)

        artigo.arquivos = json.dumps(existing) if existing else None

        db.session.commit()
        flash('Artigo enviado para revisão!', 'success')
        return redirect(url_for('meus_artigos'))

    arquivos = json.loads(artigo.arquivos or '[]')
    return render_template('artigo.html', artigo=artigo, arquivos=arquivos)

@app.route("/artigo/<int:artigo_id>/editar", methods=["GET", "POST"])
def editar_artigo(artigo_id):
    if "username" not in session:
        return redirect(url_for("login"))

    artigo = Article.query.get_or_404(artigo_id)

    # somente autor ou admin
    if session.get("role") != "admin" and artigo.author.username != session["username"]:
        flash("Você não tem permissão para editar este artigo.", "danger")
        return redirect(url_for("artigo", artigo_id=artigo_id))

    if request.method == "POST":
        acao = request.form.get("acao", "salvar")   # salvar | enviar

        # campos básicos
        artigo.titulo = request.form["titulo"]
        artigo.texto  = request.form["texto"]
        artigo.updated_at = datetime.now(timezone.utc)

        # anexos ─ exclusões + novos
        existing = json.loads(artigo.arquivos or "[]")

        # exclusões
        for fname in request.form.getlist("delete_files"):
            if fname in existing:
                existing.remove(fname)
                try:
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                except FileNotFoundError:
                    pass

        # novos uploads
        for f in request.files.getlist("files"):
            if f and f.filename:
                dest = os.path.join(app.config["UPLOAD_FOLDER"], f.filename)
                f.save(dest)
                existing.append(f.filename)

        artigo.arquivos = json.dumps(existing) if existing else None

        # se usuário clicou “Enviar para revisão”
        if acao == "enviar":
            artigo.status = ArticleStatus.PENDENTE
            # 🔔 notifica editores / admins
            editors = User.query.filter(User.role.in_(["editor", "admin"])).all()
            for dest in editors:
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
    return render_template("editar_artigo.html", artigo=artigo, arquivos=arquivos)

@app.route("/aprovacao")
def aprovacao():
    if "username" not in session or session["role"] not in ["editor", "admin"]:
        flash("Permissão negada.", "danger")
        return redirect(url_for("login"))

    pendentes = (Article.query
                 .filter_by(status=ArticleStatus.PENDENTE)
                 .order_by(Article.created_at.asc())
                 .all())

    # id do editor/admin logado
    uid = session["user_id"]
    revisados = (
        Article.query
        .join(Comment, Comment.artigo_id == Article.id)
        .filter(Comment.user_id == uid)
        .filter(Article.status != ArticleStatus.PENDENTE)
        .group_by(Article.id)                                 # ← agrupa por artigo
        .order_by(func.max(Comment.created_at).desc())        # ← último comentário
        .all()
    )

    for lista in (pendentes, revisados):
        for art in lista:
            dt = art.updated_at or art.created_at
            art.local_dt = dt.astimezone(ZoneInfo("America/Sao_Paulo"))

    return render_template(
        "aprovacao.html",
        pendentes=pendentes,
        revisados=revisados
    )

@app.route('/aprovacao/<int:artigo_id>', methods=['GET', 'POST'])
def aprovacao_detail(artigo_id):
    if 'username' not in session or session['role'] not in ['editor','admin']:
        flash('Permissão negada.', 'danger')
        return redirect(url_for('login'))

    artigo = Article.query.get_or_404(artigo_id)

    if request.method=='POST':
        acao       = request.form['acao']                 # aprovar / ajustar / rejeitar
        comentario = request.form.get('comentario','').strip()

        # 1) Atualiza o status -------------------------------------------------
        if acao == 'aprovar':
            artigo.status = ArticleStatus.APROVADO
            msg = f"Artigo '{artigo.titulo}' aprovado!"
        elif acao == 'ajustar':
            artigo.status = ArticleStatus.EM_AJUSTE
            msg = f"Artigo '{artigo.titulo}' marcado como Em Ajuste."
        elif acao == 'rejeitar':
            artigo.status = ArticleStatus.REJEITADO
            msg = f"Artigo '{artigo.titulo}' rejeitado!"
        else:
            flash('Ação desconhecida.', 'warning')
            return redirect(url_for('aprovacao_detail', artigo_id=artigo_id))

        # 2) Registra comentário de ajuste/aprovação/rejeição ------------------
        user = User.query.filter_by(username=session['username']).first()
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

        # 4) Mensagem para o editor e redirecionamento ------------------------
        flash(msg, 'success')
        return redirect(url_for('aprovacao'))

    # GET → renderiza detalhes e histórico
    arquivos = json.loads(artigo.arquivos or '[]')
    return render_template(
        'aprovacao_detail.html',
        artigo   = artigo,
        arquivos = arquivos
    )

@app.route('/solicitar_revisao/<int:artigo_id>', methods=['GET','POST'])
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

        destinatarios = [artigo.author] + User.query.filter_by(role='admin').all()
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

    return render_template('solicitar_revisao.html', artigo=artigo)

@app.route('/pesquisar')
def pesquisar():
    if 'username' not in session:
        return redirect(url_for('login'))
    q = request.args.get('q','').strip()
    query = Article.query.filter_by(status=ArticleStatus.APROVADO)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Article.titulo.ilike(like),
            Article.texto.ilike(like)
        ))
    artigos = query.order_by(Article.created_at.desc()).all()
    for art in artigos:
        dt = art.created_at or datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        art.local_created = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
    return render_template(
        'pesquisar.html',
        artigos=artigos,
        q=q,
        now=datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

@app.route('/profile_pics/<filename>')
def profile_pics(filename):
    return send_from_directory(app.config['PROFILE_PICS_FOLDER'], filename)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/perfil', methods=['GET','POST'])
def perfil():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    if request.method=='POST':
        pic = request.files.get('foto')
        if pic and pic.filename:
            fn   = f"{user.username}_{pic.filename}"
            dest = os.path.join(app.config['PROFILE_PICS_FOLDER'], fn)
            pic.save(dest)
            user.foto = fn
            db.session.commit()
            session['foto'] = fn
            flash('Foto atualizada!', 'success')
        return redirect(url_for('perfil'))
    return render_template('perfil.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)