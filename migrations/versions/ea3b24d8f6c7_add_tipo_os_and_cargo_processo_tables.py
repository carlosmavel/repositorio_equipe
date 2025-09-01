"""add tipo_os and cargo_processo tables, rename etapa_processo"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ea3b24d8f6c7'
down_revision = '52f02b1c789a'
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    """Return True if the given table exists (case-insensitive)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = {t.lower() for t in inspector.get_table_names()}
    return table.lower() in tables

def _has_fk(table: str, constraint: str) -> bool:
    """Check whether the table has a foreign key with the given name."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table.lower() not in {t.lower() for t in inspector.get_table_names()}:
        return False
    fks = {fk["name"].lower() for fk in inspector.get_foreign_keys(table)}
    return constraint.lower() in fks



def upgrade():
    # Rename etapa_processo to processo_etapa and update FK in campo_etapa
    if _has_fk('campo_etapa', 'campo_etapa_etapa_id_fkey'):
        op.drop_constraint('campo_etapa_etapa_id_fkey', 'campo_etapa', type_='foreignkey')
    if _has_table('etapa_processo'):
        op.rename_table('etapa_processo', 'processo_etapa')
    if not _has_fk('campo_etapa', 'campo_etapa_etapa_id_fkey'):
        op.create_foreign_key('campo_etapa_etapa_id_fkey', 'campo_etapa', 'processo_etapa', ['etapa_id'], ['id'])

    # Create subprocesso table
    if not _has_table('subprocesso'):
        op.create_table(
            'subprocesso',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('nome', sa.String(length=255), nullable=False),
            sa.Column('processo_id', sa.String(length=36), sa.ForeignKey('processo.id'), nullable=False),
        )

    # Create cargo_processo table
    if not _has_table('cargo_processo'):
        op.create_table(
            'cargo_processo',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('cargo_id', sa.Integer(), sa.ForeignKey('cargo.id'), nullable=False),
            sa.Column('subprocesso_id', sa.Integer(), sa.ForeignKey('subprocesso.id'), nullable=False),
        )

    # Create tipo_os table
    if not _has_table('tipo_os'):
        op.create_table(
            'tipo_os',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('nome', sa.String(length=255), nullable=False),
            sa.Column('descricao', sa.Text(), nullable=True),
            sa.Column('subprocesso_id', sa.Integer(), sa.ForeignKey('subprocesso.id'), nullable=False),
            sa.Column('equipe_responsavel_id', sa.Integer(), sa.ForeignKey('celula.id'), nullable=True),
            sa.Column('formulario_vinculado_id', sa.Integer(), nullable=True),
            sa.Column('obrigatorio_preenchimento', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        )


def downgrade():
    # Drop newly created tables
    if _has_table('tipo_os'):
        op.drop_table('tipo_os')
    if _has_table('cargo_processo'):
        op.drop_table('cargo_processo')
    if _has_table('subprocesso'):
        op.drop_table('subprocesso')

    # Rename processo_etapa back to etapa_processo and restore FK
    if _has_fk('campo_etapa', 'campo_etapa_etapa_id_fkey'):
        op.drop_constraint('campo_etapa_etapa_id_fkey', 'campo_etapa', type_='foreignkey')
    if _has_table('processo_etapa'):
        op.rename_table('processo_etapa', 'etapa_processo')
    if not _has_fk('campo_etapa', 'campo_etapa_etapa_id_fkey'):
        op.create_foreign_key('campo_etapa_etapa_id_fkey', 'campo_etapa', 'etapa_processo', ['etapa_id'], ['id'])
