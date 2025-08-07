from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
import json
import random
import os
import uuid
from werkzeug.utils import secure_filename

# Importação dos módulos de nível superior da aplicação.
# Como este blueprint está dentro do pacote "blueprints", precisamos subir um
# nível na hierarquia para acessar ``models``, ``database`` e ``decorators``.
# As importações anteriores tentavam usar ``.models`` (que procurava por um
# módulo ``models`` dentro do próprio pacote ``blueprints``) e, ao falhar,
# recorriam a um import absoluto ``models``.  Isso causava erros quando o
# aplicativo era carregado como parte do pacote ``repositorio_equipe``.
# Utilizando ``..`` garantimos que o Python procure os módulos no pacote pai.
try:
    from ..core.models import Formulario, User
    from ..core.database import db
    from ..core.decorators import form_builder_required
    from ..core.utils import user_can_access_form_builder, validar_fluxo_ramificacoes
except ImportError:  # pragma: no cover - fallback para execução direta
    from core.models import Formulario, User
    from core.database import db
    from core.decorators import form_builder_required
    from core.utils import user_can_access_form_builder, validar_fluxo_ramificacoes

formularios_bp = Blueprint('formularios_bp', __name__, url_prefix='/ordem-servico/formularios')


@formularios_bp.route('/', methods=['GET', 'POST'])
@form_builder_required
def formularios():
    aba_ativa = 'consulta'
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        estrutura = request.form.get('estrutura', '').strip()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
            aba_ativa = 'cadastro'
        else:
            valido, msg = validar_fluxo_ramificacoes(estrutura)
            if not valido:
                flash(msg, 'danger')
                aba_ativa = 'cadastro'
            else:
                f = Formulario(nome=nome, descricao=descricao, estrutura=estrutura)
                db.session.add(f)
                db.session.commit()
                flash('Formulário criado com sucesso!', 'success')
                return redirect(url_for('formularios_bp.formularios'))
    status = request.args.get('status', 'ativos')
    query = Formulario.query
    if status == 'ativos':
        query = query.filter_by(ativo=True)
    elif status == 'inativos':
        query = query.filter_by(ativo=False)
    formularios = query.order_by(Formulario.created_at.desc()).all()
    return render_template('formularios/formulario.html', formularios=formularios, aba_ativa=aba_ativa, status=status)


@formularios_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@form_builder_required
def editar_formulario(id):
    formulario = Formulario.query.get_or_404(id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        estrutura = request.form.get('estrutura', '').strip()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        else:
            valido, msg = validar_fluxo_ramificacoes(estrutura)
            if not valido:
                flash(msg, 'danger')
            else:
                formulario.nome = nome
                formulario.descricao = descricao
                formulario.estrutura = estrutura
                db.session.commit()
                flash('Formulário atualizado!', 'success')
                return redirect(url_for('formularios_bp.formularios'))
    return render_template('formularios/editar_formulario.html', formulario=formulario)


@formularios_bp.route('/<int:id>/toggle-ativo', methods=['POST'])
@form_builder_required
def toggle_ativo_formulario(id):
    formulario = Formulario.query.get_or_404(id)
    formulario.ativo = not formulario.ativo
    db.session.commit()
    status_texto = 'ativado' if formulario.ativo else 'inativado'
    flash(f'Formulário {status_texto} com sucesso!', 'success')
    return redirect(url_for('formularios_bp.formularios'))


@formularios_bp.route('/upload-imagem', methods=['POST'])
@form_builder_required
def upload_imagem():
    arquivo = request.files.get('imagem')
    if not arquivo or arquivo.filename == '':
        return jsonify({'error': 'no file'}), 400
    filename = secure_filename(arquivo.filename)
    unique = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique)
    arquivo.save(path)
    url = url_for('uploaded_file', filename=unique)
    return jsonify({'url': url})


@formularios_bp.route('/<int:id>/preencher', methods=['GET'])
def preencher_formulario(id):
    """Renderiza um formulário para preenchimento."""
    formulario = Formulario.query.get_or_404(id)
    estrutura = []
    if formulario.estrutura:
        try:
            estrutura = json.loads(formulario.estrutura)
            for bloco in estrutura:
                if bloco.get('tipo') == 'section':
                    for campo in bloco.get('campos', []):
                        if campo.get('embaralharOpcoes') and campo.get('opcoes'):
                            random.shuffle(campo['opcoes'])
                else:
                    if bloco.get('embaralharOpcoes') and bloco.get('opcoes'):
                        random.shuffle(bloco['opcoes'])
        except ValueError:
            flash('Estrutura do formulário inválida.', 'danger')
    can_edit = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user_can_access_form_builder(user):
            can_edit = True
    return render_template(
        'formularios/preencher_formulario.html',
        formulario=formulario,
        estrutura=estrutura,
        can_edit=can_edit,
    )
