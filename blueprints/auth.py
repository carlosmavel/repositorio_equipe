import os
import re
import uuid
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app as app, send_from_directory, abort
from werkzeug.utils import secure_filename
try:
    from ..core.database import db
except ImportError:
    from core.database import db

try:
    from ..core.models import User
except ImportError:
    from core.models import User

try:
    from ..core.utils import generate_token, confirm_token, send_email, password_meets_requirements
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.utils import generate_token, confirm_token, send_email, password_meets_requirements


def send_password_email(user, action):
    token = generate_token(user.id, action)
    if action == 'reset':
        url = url_for('reset_password_token', token=token, _external=True)
        action_text = 'redefinir'
    else:
        url = url_for('set_password_token', token=token, _external=True)
        action_text = 'criar'
    html = render_template('email/password_email.html', user=user, url=url, action=action_text)
    send_email(user.email, 'Definição de Senha', html)

auth_bp = Blueprint('auth_bp', __name__)

# ROTAS PRINCIPAIS
# -------------------------------------------------------------------------
@auth_bp.route('/', endpoint='index')
def index():
    if 'username' in session:
        return redirect(url_for('pesquisar'))
    return redirect(url_for('login'))

@auth_bp.route("/login", methods=["GET", "POST"], endpoint='login')
def login():
    """
    Manipula a autenticação do usuário.
    Para requisições GET, exibe o formulário de login.
    Para requisições POST, valida as credenciais. Se corretas, estabelece a sessão
    e redireciona para a página inicial do usuário. Em caso de falha no POST,
    re-renderiza o formulário de login com mensagem de erro.
    """

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Validação simples de campos vazios no backend
        if not username or not password:
            flash("Nome de usuário e senha são obrigatórios.", "danger")
            return render_template("auth/login.html", users_json={})

        user = User.query.filter_by(username=username).first()

        # Verifica as credenciais
        if user and user.check_password(password):  # Assume que o modelo User tem o método check_password
            # Credenciais corretas: estabelece a sessão
            session.clear()
            if hasattr(session, "regenerate"):
                session.regenerate()
            session["user_id"] = user.id
            session["username"] = user.username
            session["permissoes"] = [p.codigo for p in user.get_permissoes()]

            # Redireciona para a página de destino após o login
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for("pagina_inicial")) # Redireciona para a página inicial do usuário
        else:
            # Credenciais inválidas
            flash("Usuário ou senha inválidos!", "danger")
            return render_template("auth/login.html", users_json={})

    # Para requisições GET (primeiro acesso à página de login)
    return render_template("auth/login.html", users_json={})


@auth_bp.route('/esqueci-senha', methods=['GET', 'POST'], endpoint='forgot_password')
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if email:
            user = User.query.filter_by(email=email).first()
            if user:
                send_password_email(user, 'reset')
        flash('Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha.', 'info')
        return redirect(url_for('login'))
    return render_template('auth/reset_password_request.html')


@auth_bp.route('/reset-senha/<token>', methods=['GET', 'POST'], endpoint='reset_password_token')
def reset_password_token(token):
    data = confirm_token(token)
    if not data or data.get('action') != 'reset':
        flash('Link inválido ou expirado.', 'danger')
        return redirect(url_for('login'))
    user = User.query.get(data.get('user_id'))
    if not user:
        flash('Usuário inválido.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nova = request.form.get('nova_senha')
        confirmar = request.form.get('confirmar_nova_senha')
        if not nova or nova != confirmar or not password_meets_requirements(nova):
            flash('Verifique a nova senha e confirme corretamente.', 'danger')
        else:
            user.set_password(nova)
            db.session.commit()
            flash('Senha redefinida com sucesso. Faça login.', 'success')
            return redirect(url_for('login'))
    return render_template('auth/password_update.html', title='Redefinir Senha')


@auth_bp.route('/criar-senha/<token>', methods=['GET', 'POST'], endpoint='set_password_token')
def set_password_token(token):
    data = confirm_token(token)
    if not data or data.get('action') != 'create':
        flash('Link inválido ou expirado.', 'danger')
        return redirect(url_for('login'))
    user = User.query.get(data.get('user_id'))
    if not user:
        flash('Usuário inválido.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nova = request.form.get('nova_senha')
        confirmar = request.form.get('confirmar_nova_senha')
        if not nova or nova != confirmar or not password_meets_requirements(nova):
            flash('Verifique a nova senha e confirme corretamente.', 'danger')
        else:
            user.set_password(nova)
            db.session.commit()
            flash('Senha definida com sucesso. Você já pode fazer login.', 'success')
            return redirect(url_for('login'))
    return render_template('auth/password_update.html', title='Criar Senha')

@auth_bp.route('/inicio', endpoint='pagina_inicial')
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

@auth_bp.route('/profile_pics/<filename>', endpoint='profile_pics')
def profile_pics(filename):
    if 'user_id' not in session:
        app.logger.warning("Tentativa anônima de acesso a foto de perfil: %s", filename)
        return abort(401)
    return send_from_directory(app.config['PROFILE_PICS_FOLDER'], filename)

@auth_bp.route('/uploads/<filename>', endpoint='uploaded_file')
def uploaded_file(filename):
    if 'user_id' not in session:
        app.logger.warning("Tentativa anônima de acesso a upload: %s", filename)
        return abort(401)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@auth_bp.route('/perfil', methods=['GET','POST'], endpoint='perfil')
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
                 return render_template('usuarios/perfil.html', user=user,
                                       password_error=password_error, 
                                       open_password_collapse=open_password_collapse)
        
        # Se o POST não foi tratado por uma ação específica acima, redireciona para o perfil (GET)
        return redirect(url_for('perfil'))

    # Para o método GET
    return render_template('usuarios/perfil.html', user=user,
                           password_error=password_error, 
                           open_password_collapse=open_password_collapse)

@auth_bp.route('/logout', endpoint='logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

