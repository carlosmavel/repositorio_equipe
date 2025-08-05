from flask import Blueprint, render_template, request, redirect, url_for, flash

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


@formularios_bp.route('/')
@form_builder_required
def listar_formularios():
    formularios = Formulario.query.order_by(Formulario.created_at.desc()).all()
    return render_template('formularios/lista.html', formularios=formularios)


@formularios_bp.route('/novo', methods=['GET', 'POST'])
@form_builder_required
def novo_formulario():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        estrutura = request.form.get('estrutura', '').strip()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        else:
            f = Formulario(nome=nome, estrutura=estrutura)
            db.session.add(f)
            db.session.commit()
            flash('Formulário criado com sucesso!', 'success')
            return redirect(url_for('listar_formularios'))
    return render_template('formularios/form.html', formulario=None)


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
            return redirect(url_for('listar_formularios'))
    return render_template('formularios/form.html', formulario=formulario)
