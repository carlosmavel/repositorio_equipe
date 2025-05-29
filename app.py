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
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash # generate_password_hash se for resetar senha no admin
from sqlalchemy import or_, func
from functools import wraps # Essencial para decoradores, você já tinha

from database import db
from enums import ArticleStatus
from models import ( # Importando os modelos necessários
    User, Article, RevisionRequest, Notification, Comment, Attachment,
    Estabelecimento # <<< NOSSO NOVO MODELO PARA A ROTA DE ADMIN
)
from utils import sanitize_html, extract_text
# from mimetypes import guess_type # Se for usar, descomente
from werkzeug.utils import secure_filename # Útil para uploads, como na sua foto de perfil

# -------------------------------------------------------------------------
# Configuração da Aplicação (Seu código existente)
# -------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave_de_desenvolvimento_muito_segura_trocar_em_prod') # Adicionei um lembrete

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI',
    'postgresql://appuser:AppUser2025%21@localhost:5432/repositorio_equipe_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Pastas de upload (Seu código existente)
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads') # Melhor usar app.root_path para caminhos
PROFILE_PICS_FOLDER = os.path.join(app.root_path, 'Static', 'profile_pics')
for folder in (UPLOAD_FOLDER, PROFILE_PICS_FOLDER):
    os.makedirs(folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER

# -------------------------------------------------------------------------
# DECORADORES
# -------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: # Verifica se está logado
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin': # Verifica se é admin
            flash('Acesso negado. Você precisa ser um administrador para acessar esta página.', 'danger')
            # Redireciona para uma página segura, talvez o perfil ou a lista de artigos do usuário
            return redirect(url_for('meus_artigos')) # Ou 'index', ou uma página específica de "acesso negado"
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------------------------------------------------
# Context Processors
# -------------------------------------------------------------------------
@app.context_processor
def inject_notificacoes():
    if 'user_id' in session: # Usar user_id é mais seguro que username para buscar no banco
        user = User.query.get(session['user_id']) # Usar .get() é mais direto para PK
        if user:
            notifs = (Notification.query
                      .filter_by(user_id=user.id, lido=False)
                      .order_by(Notification.created_at.desc())
                      .limit(10)
                      .all())
            return {
                'notificacoes': len(notifs), # Passa a contagem diretamente
                'notificacoes_list': notifs
            }
    return {'notificacoes': 0, 'notificacoes_list': []}

@app.context_processor
def inject_enums():
    return dict(ArticleStatus=ArticleStatus)

@app.context_processor
def inject_current_user():
    if 'user_id' in session:
        return {'current_user': User.query.get(session['user_id'])}
    return {'current_user': None}

@app.context_processor
def inject_zoneinfo():
    return dict(ZoneInfo=ZoneInfo)

# -------------------------------------------------------------------------
# ROTAS DE ADMINISTRAÇÃO (NOVA SEÇÃO - ADICIONE AS ROTAS DO ADMIN AQUI)
# -------------------------------------------------------------------------
@app.route('/admin/')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/estabelecimentos', methods=['GET', 'POST'])
@admin_required
def admin_estabelecimentos():
    # Lógica do CRUD de estabelecimentos virá aqui depois.
    # Por enquanto, para testar o layout e os links:
    if request.method == 'POST':
        # Exemplo de como seria para adicionar/editar (vamos detalhar depois)
        codigo = request.form.get('codigo')
        nome = request.form.get('nome')
        id_para_atualizar = request.form.get('id_para_atualizar')
        if not codigo or not nome:
            flash('Código e Nome são obrigatórios.', 'danger')
        else:
            # Lógica de salvar/atualizar...
            flash(f'Estabelecimento {nome} processado (implementar save!).', 'success')
        return redirect(url_for('admin_estabelecimentos'))
    
    estabelecimentos = Estabelecimento.query.order_by(Estabelecimento.nome).all()
    est_editar_id = request.args.get('edit_id', type=int)
    est_editar = None
    if est_editar_id:
        est_editar = Estabelecimento.query.get(est_editar_id)
        
    return render_template('admin/estabelecimentos.html', 
                           estabelecimentos=estabelecimentos, 
                           est_editar=est_editar)

# -------------------------------------------------------------------------
# ROTAS PRINCIPAIS
# -------------------------------------------------------------------------
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('pesquisar'))
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Manipula a autenticação do usuário e exibe o preview de fotos na página de login.
    Para requisições GET, exibe o formulário de login.
    Para requisições POST, valida as credenciais. Se corretas, estabelece a sessão
    e redireciona para a página inicial do usuário. Em caso de falha no POST,
    re-renderiza o formulário de login com mensagem de erro, mantendo o preview de fotos.
    """
    
    # Prepara users_json para o preview de fotos.
    # Esta variável estará disponível tanto para o GET quanto para o POST com erro.
    users_data_for_preview = {}
    try:
        # Tenta buscar todos os usuários para o preview.
        # Envolve em try-except para o caso da tabela User não existir ou outro erro de DB.
        all_users = User.query.all()
        users_data_for_preview = {
            user.username: {"foto": user.foto or ""} for user in all_users
        }
    except Exception as e:
        app.logger.error(f"Erro ao buscar usuários para preview de foto no login: {str(e)}")
        # Em caso de erro, users_data_for_preview continuará como um dicionário vazio.

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Validação simples de campos vazios no backend
        if not username or not password:
            flash("Nome de usuário e senha são obrigatórios.", "danger")
            # Re-renderiza o formulário com users_data_for_preview para manter o preview de fotos
            return render_template("login.html", users_json=users_data_for_preview)

        user = User.query.filter_by(username=username).first()

        # Verifica as credenciais
        if user and user.check_password(password): # Assume que o modelo User tem o método check_password
            # Credenciais corretas: estabelece a sessão
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            
            # Redireciona para a página de destino após o login
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for("pagina_inicial")) # Redireciona para a página inicial do usuário
        else:
            # Credenciais inválidas
            flash("Usuário ou senha inválidos!", "danger")
            # Re-renderiza o formulário com users_data_for_preview para manter o preview de fotos
            return render_template("login.html", users_json=users_data_for_preview)
    
    # Para requisições GET (primeiro acesso à página de login)
    return render_template("login.html", users_json=users_data_for_preview)

@app.route('/inicio')
def pagina_inicial():
    """
    Renderiza a página inicial do usuário após o login.
    Verifica se o usuário está logado antes de exibir a página.
    No futuro, esta rota poderá carregar dados específicos para personalizar o dashboard do usuário.
    """
    if 'user_id' not in session: # Verificação de sessão de usuário
        flash("Por favor, faça login para acessar esta página.", "warning")
        # Redireciona para a página de login, passando a URL atual como próximo destino
        return redirect(url_for('login', next=request.url)) 
    
    # Atualmente, apenas renderiza o template.
    # Em futuras implementações, dados do dashboard seriam carregados aqui.
    # Ex: widgets_data = carregar_dados_dashboard(session['user_id'])
    # return render_template('pagina_inicial.html', widgets=widgets_data)
    return render_template('pagina_inicial.html')

@app.route('/novo-artigo', methods=['GET', 'POST'])
def novo_artigo():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Só colaboradores, editores e admins podem criar
    if request.method == 'POST' and session['role'] in ['colaborador', 'editor', 'admin']:
        import os, uuid, json, time
        from datetime import datetime, timezone
        from werkzeug.utils import secure_filename
        from mimetypes import guess_type
        from utils import sanitize_html, extract_text
        from models import User, Article, Attachment, Notification

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

        # 2) Cria o artigo (sem arquivos ainda) e dá um flush para ter ID
        user = User.query.filter_by(username=session['username']).first()
        artigo = Article(
            titulo     = titulo,
            texto      = texto_limpo,
            status     = status,
            user_id    = user.id,
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
                original   = secure_filename(f.filename)
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

        # 6) Notifica editores/admins, se necessário
        if status is ArticleStatus.PENDENTE:
            destinatarios = User.query.filter(User.role.in_(['editor', 'admin'])).all()
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

                # === Aqui mesmo, dentro do loop, extraímos e criamos o Attachment ===
                from mimetypes import guess_type
                from utils import extract_text
                from models import Attachment

                # 1) extrai texto
                texto_extraido = extract_text(dest)
                # 2) descobre o MIME
                mime_type, _ = guess_type(dest)
                # 3) adiciona o attachment ao session
                attachment = Attachment(
                    article=artigo,
                    filename=f.filename,
                    mime_type=mime_type or "application/octet-stream",
                    content=texto_extraido
                )
                db.session.add(attachment)

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
        like   = f"%{q}%"
        ts_q   = func.plainto_tsquery('portuguese', q)

        # subquery: todos os artigos cujos anexos batem no tsquery
        sub = (
            db.session.query(Attachment.article_id)
            .filter(
                func.to_tsvector('portuguese', Attachment.content)
                .op('@@')(ts_q)
            )
            .subquery()
        )

        query = query.filter(
            or_(
                Article.titulo.ilike(like),
                Article.texto.ilike(like),
                Article.id.in_(sub)
            )
        )

    artigos = query.order_by(Article.created_at.desc()).all()

    # formata datas para o fuso local
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
    if 'user_id' not in session:
        flash("Faça login para acessar seu perfil.", "warning")
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(session['user_id'])
    
    password_error = None
    open_password_collapse = False

    if request.method == 'POST':
        action = request.form.get('action')

        # Lógica para upload de foto
        if 'foto' in request.files and request.files['foto'].filename != '':
            pic = request.files['foto']
            
            if pic and pic.filename: # Confirma que temos um arquivo com nome
                original_filename = secure_filename(pic.filename)

                if original_filename != '':
                    _, ext = os.path.splitext(original_filename)
                    unique_filename = f"{user.username}_{uuid.uuid4().hex}{ext.lower()}"
                    save_folder = app.config['PROFILE_PICS_FOLDER']
                    save_path = os.path.join(save_folder, unique_filename)
                    
                    try:
                        # Deletar foto antiga do disco, se existir
                        if user.foto:
                            old_foto_path = os.path.join(save_folder, user.foto)
                            if os.path.exists(old_foto_path):
                                try:
                                    os.remove(old_foto_path)
                                except Exception as e_del:
                                    app.logger.error(f"Erro ao tentar deletar foto antiga '{user.foto}': {str(e_del)}") # Log do erro
                        
                        pic.save(save_path)
                        user.foto = unique_filename
                        db.session.commit()
                        flash('Foto de perfil atualizada com sucesso!', 'success')
                    
                    except Exception as e:
                        db.session.rollback()
                        app.logger.error(f"ERRO CRÍTICO AO SALVAR ARQUIVO OU COMMITAR FOTO: {str(e)}") # Log do erro
                        flash('Ocorreu um erro crítico ao tentar salvar sua foto de perfil.', 'danger')
                else:
                    flash('Nome de arquivo inválido ou não permitido após limpeza.', 'warning')
            else:
                flash('Nenhum arquivo de foto válido foi selecionado ou o nome do arquivo está ausente.', 'warning')
            
            return redirect(url_for('perfil'))

        elif action == 'update_info':
            user.nome_completo = request.form.get('nome_completo', user.nome_completo).strip()
            user.telefone_contato = request.form.get('telefone_contato', user.telefone_contato)
            user.ramal = request.form.get('ramal', user.ramal)
            
            data_nascimento_str = request.form.get('data_nascimento')
            if data_nascimento_str:
                try:
                    user.data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de nascimento inválida. Use o formato AAAA-MM-DD.', 'danger')
                    # Mantém outras alterações, mas não salva a data inválida ou poderia retornar aqui
            else:
                user.data_nascimento = None 
            
            try:
                db.session.commit()
                flash('Informações do perfil atualizadas!', 'success')
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"ERRO AO ATUALIZAR INFO PERFIL: {str(e)}") # Log do erro
                flash('Erro ao atualizar informações do perfil.', 'danger')
            return redirect(url_for('perfil'))

        elif action == 'change_password':
            open_password_collapse = True
            senha_atual = request.form.get('senha_atual')
            nova_senha = request.form.get('nova_senha')
            confirmar_nova_senha = request.form.get('confirmar_nova_senha')

            if not senha_atual or not nova_senha or not confirmar_nova_senha:
                password_error = 'Todos os campos de senha são obrigatórios.'
            elif not user.check_password(senha_atual):
                password_error = 'Senha atual incorreta.'
            elif nova_senha != confirmar_nova_senha:
                password_error = 'A nova senha e a confirmação não coincidem.'
            elif len(nova_senha) < 8 or \
                 not re.search(r"[A-Z]", nova_senha) or \
                 not re.search(r"[a-z]", nova_senha) or \
                 not re.search(r"[0-9]", nova_senha) or \
                 not re.search(r"[!@#$%^&*(),.?\":{}|<>]", nova_senha):
                password_error = 'A nova senha não atende aos requisitos de segurança.'
            else:
                user.set_password(nova_senha)
                try:
                    db.session.commit()
                    flash('Senha alterada com sucesso! Por favor, faça login novamente.', 'success')
                    session.clear() 
                    return redirect(url_for('login'))
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"ERRO AO SALVAR NOVA SENHA: {str(e)}") # Log do erro
                    password_error = "Erro ao salvar a nova senha. Tente novamente."

            if password_error: # Se alguma validação de senha falhou
                 return render_template('perfil.html', user=user, 
                                       password_error=password_error, 
                                       open_password_collapse=open_password_collapse)
        
        # Se o POST não foi tratado por uma ação específica acima, redireciona para o perfil (GET)
        return redirect(url_for('perfil'))

    # Para o método GET
    return render_template('perfil.html', user=user, 
                           password_error=password_error, 
                           open_password_collapse=open_password_collapse)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)