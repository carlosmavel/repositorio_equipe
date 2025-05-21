import os
import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory, flash
from flask_migrate import Migrate
from sqlalchemy import or_
from database import db
from models import Article, RevisionRequest, Notification, User

# -----------------------------------------------------------------------------
# Configuração da Aplicação
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave_de_desenvolvimento')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI',
    'postgresql://appuser:AppUser2025%21@localhost:5432/repositorio_equipe_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o banco de dados e o migrator
# 'db' está definido em models.py
db.init_app(app)
migrate = Migrate(app, db)

# Agora que o db está inicializado, importe os models
from models import User, Article, RevisionRequest


# Configuração de pastas para uploads
UPLOAD_FOLDER = 'uploads'
PROFILE_PICS_FOLDER = 'profile_pics'
for folder in [UPLOAD_FOLDER, PROFILE_PICS_FOLDER]:
    os.makedirs(folder, exist_ok=True)
    if not os.access(folder, os.W_OK):
        print(f"Sem permissão de escrita em {folder}.")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER

# -----------------------------------------------------------------------------
# Processador de Contexto: Notificações
# -----------------------------------------------------------------------------
@app.context_processor
def inject_notificacoes():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            # busca apenas notificações ainda não lidas
            notifs = (
                Notification.query
                .filter_by(user_id=user.id, lido=False)
                .order_by(Notification.created_at.desc())
                .all()
            )
            return {
                'notificacoes': len(notifs),
                'notificacoes_list': notifs
            }
    return {'notificacoes': 0, 'notificacoes_list': []}


# -----------------------------------------------------------------------------
# Rotas da Aplicação
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('pesquisar'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = user.username
            session['role']     = user.role
            session['foto']     = user.foto
            session['nome_completo'] = user.nome_completo
            return redirect(url_for('pesquisar'))
        flash('Usuário ou senha inválidos!', 'danger')
        return redirect(url_for('login'))

    # GET: preparar o JSON de usuários para o preview das fotos
    users = User.query.all()
    users_json = json.dumps({
        u.username: {'foto': u.foto}
        for u in users
    })

    return render_template('login.html', users_json=users_json)


@app.route('/novo-artigo', methods=['GET', 'POST'])
def novo_artigo():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST' and session['role'] in ['colaborador', 'editor', 'admin']:
        from models import User, Article, Notification
        # 1) Coleta dados do formulário
        titulo = request.form['titulo']
        texto  = request.form['texto']
        files  = request.files.getlist('files')

        # 2) Salva arquivos e monta lista de nomes
        filenames = []
        for f in files:
            if f and f.filename:
                path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
                f.save(path)
                filenames.append(f.filename)

        # 3) Cria o artigo no banco
        user = User.query.filter_by(username=session['username']).first()
        artigo = Article(
            titulo    = titulo,
            texto     = texto,
            status    = 'pendente',
            user_id   = user.id,
            arquivos  = json.dumps(filenames) if filenames else None,
            created_at = datetime.now(timezone.utc),
            updated_at = datetime.now(timezone.utc)
        )
        db.session.add(artigo)
        db.session.commit()

        # 4) Notifica todos os editores e admins
        destinatarios = User.query.filter(User.role.in_(['editor','admin'])).all()
        for u in destinatarios:
            n = Notification(
                user_id = u.id,
                message = f"Novo artigo “{artigo.titulo}” submetido por {user.username}",
                url     = url_for('aprovacao')
            )
            db.session.add(n)
        db.session.commit()

        flash('Artigo criado com sucesso!', 'success')
        time.sleep(1)
        return redirect(url_for('meus_artigos'))

    return render_template('novo_artigo.html')

@app.route('/meus-artigos')
def meus_artigos():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Pega o usuário logado
    user = User.query.filter_by(username=session['username']).first_or_404()

    # Busca e ordena os artigos deste usuário (mais recentes primeiro)
    artigos = (
        Article.query
               .filter_by(user_id=user.id)
               .order_by(Article.created_at.desc())
               .all()
    )

    # Converte created_at (UTC) para horário de São Paulo
    for art in artigos:
        dt = art.created_at
        # se for naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        art.local_created = dt.astimezone(ZoneInfo("America/Sao_Paulo"))

    return render_template(
        'meus_artigos.html',
        artigos=artigos,
        now=datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

@app.route('/artigo/<int:artigo_id>', methods=['GET', 'POST'])
def artigo(artigo_id):
    # só usuários logados podem ver a página
    if 'username' not in session:
        return redirect(url_for('login'))

    # busca o artigo (ou 404)
    artigo = Article.query.get_or_404(artigo_id)

    if request.method == 'POST':
        # somente o autor ou o admin podem salvar mudanças
        if session['role'] != 'admin' and artigo.author.username != session['username']:
            flash('Você não tem permissão para editar esse artigo.', 'danger')
            return redirect(url_for('meus_artigos'))

        # atualiza título e texto
        artigo.titulo = request.form['titulo']
        artigo.texto = request.form['texto']

        # processa anexos novos
        files = request.files.getlist('files')
        existing = json.loads(artigo.arquivos) if artigo.arquivos else []
        for f in files:
            if f.filename:
                path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
                f.save(path)
                existing.append(f.filename)
        artigo.arquivos = json.dumps(existing) if existing else None

        # volta status para pendente e salva
        artigo.status = 'pendente'
        db.session.commit()
        flash('Artigo atualizado!', 'success')
        return redirect(url_for('meus_artigos'))

    # GET: apenas renderiza, sem checar permissão de edição
    arquivos = json.loads(artigo.arquivos) if artigo.arquivos else []
    return render_template('artigo.html', artigo=artigo, arquivos=arquivos)


@app.route('/aprovacao', methods=['GET'])
def aprovacao():
    # Verifica se está logado e se é editor ou admin
    if 'username' not in session or session['role'] not in ['editor', 'admin']:
        flash('Permissão negada.', 'danger')
        return redirect(url_for('login'))

    # Busca todos os artigos pendentes, do mais antigo para o mais novo
    pendentes = (
        Article.query
               .filter_by(status='pendente')
               .order_by(Article.created_at.asc())
               .all()
    )

    # Converte cada created_at (UTC) para horário de São Paulo
    for art in pendentes:
        dt = art.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        art.local_created = dt.astimezone(ZoneInfo("America/Sao_Paulo"))

    # Renderiza o template, passando apenas a lista 'pendentes'
    return render_template('aprovacao.html', lista_pendentes=pendentes)


# ---------------------------------------------------------------------
# Rota de Detalhe de Aprovação
# ---------------------------------------------------------------------
@app.route('/aprovacao/<int:artigo_id>', methods=['GET', 'POST'])
def aprovacao_detail(artigo_id):
    # Permissão
    if 'username' not in session or session['role'] not in ['editor', 'admin']:
        flash('Permissão negada.', 'danger')
        return redirect(url_for('login'))

    # ← Aqui garantimos que artigo é sempre o objeto do modelo
    artigo = Article.query.get_or_404(artigo_id)

    if request.method == 'POST':
        # Salva comentário do revisor
        comentario = request.form.get('comentario', '').strip()
        artigo.review_comment = comentario

        # Escolhe ação
        acao = request.form['acao']
        if acao == 'aprovar':
            artigo.status = 'aprovado'
            msg = f"Artigo '{artigo.titulo}' aprovado com sucesso!"
        elif acao == 'ajustar':
            artigo.status = 'em_ajuste'
            msg = f"Artigo '{artigo.titulo}' marcado como pendente de ajustes."
        elif acao == 'rejeitar':
            artigo.status = 'rejeitado'
            msg = f"Artigo '{artigo.titulo}' rejeitado!"
        else:
            flash('Ação desconhecida.', 'warning')
            return redirect(url_for('aprovacao_detail', artigo_id=artigo_id))

        db.session.commit()

        # Notificação ao autor
        notif = Notification(
            user_id=artigo.user_id,
            message=f"Seu artigo \"{artigo.titulo}\" foi {artigo.status.replace('_',' ')}",
            url=url_for('artigo', artigo_id=artigo.id)
        )
        db.session.add(notif)
        db.session.commit()

        flash(msg, 'success')
        return redirect(url_for('aprovacao'))

    # GET: desserializa anexos e renderiza
    arquivos = json.loads(artigo.arquivos or '[]')
    return render_template(
        'aprovacao_detail.html',
        artigo=artigo,
        arquivos=arquivos
    )


# ---------------------------------------------------------------------
# Rota de Solicitação de Revisão
# ---------------------------------------------------------------------
@app.route('/solicitar_revisao/<int:artigo_id>', methods=['GET', 'POST'])
def solicitar_revisao(artigo_id):
    # só usuários logados podem solicitar
    if 'username' not in session:
        return redirect(url_for('login'))

    # busca o artigo ou 404
    artigo = Article.query.get_or_404(artigo_id)
    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        comentario = request.form.get('comentario', '').strip()
        if not comentario:
            flash('Por favor, insira um comentário para a revisão.', 'warning')
            return redirect(url_for('solicitar_revisao', artigo_id=artigo.id))

        # 1) cria o pedido de revisão
        rr = RevisionRequest(
            artigo_id=artigo.id,
            user_id=user.id,
            comentario=comentario
        )
        db.session.add(rr)

        # 2) atualiza o status do artigo
        artigo.status = 'in_review'

        # 3) salva tudo
        db.session.commit()

        # 4) notifica autor + administradores
        destinatarios = [User.query.get(artigo.author_id)] + User.query.filter_by(role='admin').all()
        for u in destinatarios:
            n = Notification(
                user_id=u.id,
                message=f"{user.username} solicitou revisão de “{artigo.title}”",
                url=url_for('artigo', artigo_id=artigo.id)
            )
            db.session.add(n)
        db.session.commit()

        flash('Pedido de revisão enviado com sucesso!', 'success')
        return redirect(url_for('artigo', artigo_id=artigo.id))

    # GET: exibe o formulário
    return render_template('solicitar_revisao.html', artigo=artigo)

@app.route('/pesquisar')
def pesquisar():
    if 'username' not in session:
        return redirect(url_for('login'))

    q = request.args.get('q', '').strip()

    # Começa com todos os aprovados
    query = Article.query.filter_by(status='aprovado')

    # Se houver termo, filtra por título OU texto (case-insensitive)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Article.titulo.ilike(pattern),
                Article.texto.ilike(pattern)
            )
        )

    # Ordena do mais recente para o mais antigo
    artigos = query.order_by(Article.created_at.desc()).all()

    # Converte created_at para horário local
    for art in artigos:
        dt = art.created_at
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

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    if request.method == 'POST':
        pic = request.files.get('foto')
        if pic and pic.filename:
            fn = f"{user.username}_{pic.filename}"
            path = os.path.join(app.config['PROFILE_PICS_FOLDER'], fn)
            pic.save(path)
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