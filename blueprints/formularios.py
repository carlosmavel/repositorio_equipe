from flask import Blueprint, render_template, request, redirect, url_for, flash
import json

# Importação dos módulos de nível superior da aplicação.
# Como este blueprint está dentro do pacote "blueprints", precisamos subir um
# nível na hierarquia para acessar ``models``, ``database`` e ``decorators``.
# As importações anteriores tentavam usar ``.models`` (que procurava por um
# módulo ``models`` dentro do próprio pacote ``blueprints``) e, ao falhar,
# recorriam a um import absoluto ``models``.  Isso causava erros quando o
# aplicativo era carregado como parte do pacote ``repositorio_equipe``.
# Utilizando ``..`` garantimos que o Python procure os módulos no pacote pai.
try:
    from ..models import Formulario
    from ..database import db
    from ..decorators import form_builder_required
except ImportError:  # pragma: no cover - fallback para execução direta
    from models import Formulario
    from database import db
    from decorators import form_builder_required

formularios_bp = Blueprint('formularios_bp', __name__, url_prefix='/ordem-servico/formularios')


@formularios_bp.route('/', methods=['GET', 'POST'])
@form_builder_required
def formularios():
    aba_ativa = 'consulta'
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        estrutura = request.form.get('estrutura', '').strip()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
            aba_ativa = 'cadastro'
        else:
            f = Formulario(nome=nome, estrutura=estrutura)
            db.session.add(f)
            db.session.commit()
            flash('Formulário criado com sucesso!', 'success')
            return redirect(url_for('formularios_bp.formularios'))
    formularios = Formulario.query.order_by(Formulario.created_at.desc()).all()
    return render_template('formularios/formulario.html', formularios=formularios, aba_ativa=aba_ativa)


@formularios_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@form_builder_required
def editar_formulario(id):
    formulario = Formulario.query.get_or_404(id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        estrutura = request.form.get('estrutura', '').strip()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        else:
            formulario.nome = nome
            formulario.estrutura = estrutura
            db.session.commit()
            flash('Formulário atualizado!', 'success')
            return redirect(url_for('formularios_bp.formularios'))
    return render_template('formularios/editar_formulario.html', formulario=formulario)


@formularios_bp.route('/<int:id>/preencher', methods=['GET'])
@form_builder_required
def preencher_formulario(id):
    """Renderiza um formulário para teste de preenchimento."""
    formulario = Formulario.query.get_or_404(id)
    estrutura = []
    if formulario.estrutura:
        try:
            estrutura = json.loads(formulario.estrutura)
        except ValueError:
            flash('Estrutura do formulário inválida.', 'danger')
    return render_template(
        'formularios/preencher_formulario.html',
        formulario=formulario,
        estrutura=estrutura,
    )
