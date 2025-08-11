from alembic import op
import sqlalchemy as sa

revision = 'f1b2c3d4e5f6'
down_revision = '6b6b76d9b5e5'
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns(table)}
    return column in cols


def upgrade():
    if not _has_column('processo_etapa', 'categoria'):
        op.add_column('processo_etapa', sa.Column('categoria', sa.String(255), nullable=True))
    if not _has_column('processo_etapa', 'formulario_padrao_id'):
        op.add_column('processo_etapa', sa.Column('formulario_padrao_id', sa.Integer(), nullable=True))
        op.create_foreign_key('processo_etapa_formulario_padrao_id_fkey', 'processo_etapa', 'formulario', ['formulario_padrao_id'], ['id'])

    if not _has_table('processo_etapa_tipo_os'):
        op.create_table(
            'processo_etapa_tipo_os',

            sa.Column('etapa_id', sa.String(36), sa.ForeignKey('processo_etapa.id'), primary_key=True),

            sa.Column('tipo_os_id', sa.Integer(), sa.ForeignKey('tipo_os.id'), primary_key=True)
        )
    if not _has_table('processo_etapa_cargo_abre'):
        op.create_table(
            'processo_etapa_cargo_abre',

            sa.Column('etapa_id', sa.String(36), sa.ForeignKey('processo_etapa.id'), primary_key=True),

            sa.Column('cargo_id', sa.Integer(), sa.ForeignKey('cargo.id'), primary_key=True)
        )
    if not _has_table('processo_etapa_cargo_atende'):
        op.create_table(
            'processo_etapa_cargo_atende',

            sa.Column('etapa_id', sa.String(36), sa.ForeignKey('processo_etapa.id'), primary_key=True),

            sa.Column('cargo_id', sa.Integer(), sa.ForeignKey('cargo.id'), primary_key=True)
        )
    if not _has_table('processo_etapa_article'):
        op.create_table(
            'processo_etapa_article',

            sa.Column('etapa_id', sa.String(36), sa.ForeignKey('processo_etapa.id'), primary_key=True),

            sa.Column('article_id', sa.Integer(), sa.ForeignKey('article.id'), primary_key=True)
        )

    if _has_table('cargo_processo'):
        op.drop_table('cargo_processo')
    if _has_table('subprocesso'):
        op.drop_table('subprocesso')

    if _has_column('tipo_os', 'subprocesso_id'):
        op.drop_constraint('tipo_os_subprocesso_id_fkey', 'tipo_os', type_='foreignkey')
        op.drop_column('tipo_os', 'subprocesso_id')


def downgrade():
    if not _has_table('subprocesso'):
        op.create_table(
            'subprocesso',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('nome', sa.String(255), nullable=False),
            sa.Column('processo_id', sa.String(36), sa.ForeignKey('processo.id'), nullable=False)
        )
    if not _has_table('cargo_processo'):
        op.create_table(
            'cargo_processo',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('cargo_id', sa.Integer(), sa.ForeignKey('cargo.id'), nullable=False),
            sa.Column('subprocesso_id', sa.Integer(), sa.ForeignKey('subprocesso.id'), nullable=False)
        )
    if not _has_column('tipo_os', 'subprocesso_id'):
        op.add_column('tipo_os', sa.Column('subprocesso_id', sa.Integer(), sa.ForeignKey('subprocesso.id'), nullable=True))

    for table in ['processo_etapa_article', 'processo_etapa_cargo_atende', 'processo_etapa_cargo_abre', 'processo_etapa_tipo_os']:
        if _has_table(table):
            op.drop_table(table)
    if _has_column('processo_etapa', 'formulario_padrao_id'):
        op.drop_constraint('processo_etapa_formulario_padrao_id_fkey', 'processo_etapa', type_='foreignkey')
        op.drop_column('processo_etapa', 'formulario_padrao_id')
    if _has_column('processo_etapa', 'categoria'):
        op.drop_column('processo_etapa', 'categoria')
