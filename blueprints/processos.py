from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app as app

try:
    from ..core.database import db
except ImportError:  # pragma: no cover
    from core.database import db

try:
    from ..core.models import Processo, EtapaProcesso, CampoEtapa, Setor, Celula
except ImportError:  # pragma: no cover
    from core.models import Processo, EtapaProcesso, CampoEtapa, Setor, Celula

try:
    from ..core.decorators import admin_required
except ImportError:  # pragma: no cover
    from core.decorators import admin_required

processos_bp = Blueprint('processos_bp', __name__)

@processos_bp.route('/admin/processos', methods=['GET', 'POST'])
@admin_required
def admin_processos():
    processo_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id')
        if edit_id:
            processo_para_editar = Processo.query.get_or_404(edit_id)
    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo_check') == 'on'

        if not nome:
            flash('Nome do processo é obrigatório.', 'danger')
        else:
            query_nome = Processo.query.filter_by(nome=nome)
            if id_para_atualizar:
                query_nome = query_nome.filter(Processo.id != id_para_atualizar)
            nome_existente = query_nome.first()
            if nome_existente:
                flash(f'O nome "{nome}" já está em uso.', 'danger')
            else:
                if id_para_atualizar:
                    proc = Processo.query.get_or_404(id_para_atualizar)
                    proc.nome = nome
                    proc.descricao = descricao
                    proc.ativo = ativo
                    action_msg = 'atualizado'
                else:
                    proc = Processo(nome=nome, descricao=descricao, ativo=ativo)
                    db.session.add(proc)
                    action_msg = 'criado'
                try:
                    db.session.commit()
                    flash(f'Processo {action_msg} com sucesso!', 'success')
                    return redirect(url_for('processos_bp.admin_processos'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao salvar processo: {str(e)}', 'danger')
        if id_para_atualizar:
            processo_para_editar = Processo.query.get(id_para_atualizar)

    processos = Processo.query.order_by(Processo.nome).all()
    return render_template('admin/processos.html', processos=processos, processo_editar=processo_para_editar)

@processos_bp.route('/admin/processos/toggle_ativo/<processo_id>', methods=['POST'])
@admin_required
def admin_toggle_ativo_processo(processo_id):
    proc = Processo.query.get_or_404(processo_id)
    proc.ativo = not proc.ativo
    try:
        db.session.commit()
        status_texto = 'ativado' if proc.ativo else 'desativado'
        flash(f'Processo "{proc.nome}" foi {status_texto} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do processo: {str(e)}', 'danger')
    return redirect(url_for('processos_bp.admin_processos'))

@processos_bp.route('/admin/processos/<processo_id>/etapas', methods=['GET', 'POST'])
@admin_required
def admin_etapas(processo_id):
    proc = Processo.query.get_or_404(processo_id)
    etapa_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id')
        if edit_id:
            etapa_para_editar = EtapaProcesso.query.get_or_404(edit_id)
    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        ordem = request.form.get('ordem', type=int)
        setor_responsavel_id = request.form.get('setor_responsavel_id', type=int)
        celula_responsavel_id = request.form.get('celula_responsavel_id', type=int)
        descricao = request.form.get('descricao', '').strip()
        instrucoes = request.form.get('instrucoes', '').strip()
        if not nome or ordem is None:
            flash('Nome e ordem são obrigatórios.', 'danger')
        else:
            if id_para_atualizar:
                etapa = EtapaProcesso.query.get_or_404(id_para_atualizar)
                etapa.nome = nome
                etapa.ordem = ordem
                etapa.setor_responsavel_id = setor_responsavel_id
                etapa.celula_responsavel_id = celula_responsavel_id
                etapa.descricao = descricao
                etapa.instrucoes = instrucoes
                action_msg = 'atualizada'
            else:
                etapa = EtapaProcesso(
                    nome=nome,
                    ordem=ordem,
                    processo_id=proc.id,
                    setor_responsavel_id=setor_responsavel_id,
                    celula_responsavel_id=celula_responsavel_id,
                    descricao=descricao,
                    instrucoes=instrucoes,
                )
                db.session.add(etapa)
                action_msg = 'criada'
            try:
                db.session.commit()
                flash(f'Etapa {action_msg} com sucesso!', 'success')
                return redirect(url_for('processos_bp.admin_etapas', processo_id=proc.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar etapa: {str(e)}', 'danger')
        if id_para_atualizar:
            etapa_para_editar = EtapaProcesso.query.get(id_para_atualizar)

    etapas = proc.etapas.order_by(EtapaProcesso.ordem).all()
    setores = Setor.query.order_by(Setor.nome).all()
    celulas = Celula.query.order_by(Celula.nome).all()
    return render_template('admin/etapas.html', processo=proc, etapas=etapas, etapa_editar=etapa_para_editar, setores=setores, celulas=celulas)

@processos_bp.route('/admin/etapas/delete/<etapa_id>', methods=['POST'])
@admin_required
def admin_delete_etapa(etapa_id):
    etapa = EtapaProcesso.query.get_or_404(etapa_id)
    proc_id = etapa.processo_id
    try:
        db.session.delete(etapa)
        db.session.commit()
        flash('Etapa removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover etapa: {str(e)}', 'danger')
    return redirect(url_for('processos_bp.admin_etapas', processo_id=proc_id))

@processos_bp.route('/admin/etapas/<etapa_id>/campos', methods=['GET', 'POST'])
@admin_required
def admin_campos(etapa_id):
    etapa = EtapaProcesso.query.get_or_404(etapa_id)
    campo_para_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id')
        if edit_id:
            campo_para_editar = CampoEtapa.query.get_or_404(edit_id)
    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        nome = request.form.get('nome', '').strip()
        tipo = request.form.get('tipo', '').strip()
        obrigatorio = request.form.get('obrigatorio_check') == 'on'
        opcoes = request.form.get('opcoes')
        dica = request.form.get('dica')
        opcoes_json = [o.strip() for o in opcoes.split(',')] if opcoes else None
        if not nome or not tipo:
            flash('Nome e tipo são obrigatórios.', 'danger')
        else:
            if id_para_atualizar:
                campo = CampoEtapa.query.get_or_404(id_para_atualizar)
                campo.nome = nome
                campo.tipo = tipo
                campo.obrigatorio = obrigatorio
                campo.opcoes = opcoes_json
                campo.dica = dica
                action_msg = 'atualizado'
            else:
                campo = CampoEtapa(
                    etapa_id=etapa.id,
                    nome=nome,
                    tipo=tipo,
                    obrigatorio=obrigatorio,
                    opcoes=opcoes_json,
                    dica=dica,
                )
                db.session.add(campo)
                action_msg = 'criado'
            try:
                db.session.commit()
                flash(f'Campo {action_msg} com sucesso!', 'success')
                return redirect(url_for('processos_bp.admin_campos', etapa_id=etapa.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar campo: {str(e)}', 'danger')
        if id_para_atualizar:
            campo_para_editar = CampoEtapa.query.get(id_para_atualizar)

    campos = etapa.campos.order_by(CampoEtapa.nome).all()
    return render_template('admin/campos.html', etapa=etapa, campos=campos, campo_editar=campo_para_editar)

@processos_bp.route('/admin/campos/delete/<campo_id>', methods=['POST'])
@admin_required
def admin_delete_campo(campo_id):
    campo = CampoEtapa.query.get_or_404(campo_id)
    etapa_id = campo.etapa_id
    try:
        db.session.delete(campo)
        db.session.commit()
        flash('Campo removido com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover campo: {str(e)}', 'danger')
    return redirect(url_for('processos_bp.admin_campos', etapa_id=etapa_id))
