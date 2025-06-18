"""Add article visibility fields"""

from alembic import op
import sqlalchemy as sa

revision = 'b9bcef2efe2d'
down_revision = 'b21bf94c6932'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('article', sa.Column('visibility', sa.String(length=20), nullable=False, server_default='celula'))
    op.add_column('article', sa.Column('instituicao_id', sa.Integer(), nullable=True))
    op.add_column('article', sa.Column('estabelecimento_id', sa.Integer(), nullable=True))
    op.add_column('article', sa.Column('setor_id', sa.Integer(), nullable=True))
    op.add_column('article', sa.Column('vis_celula_id', sa.Integer(), nullable=True))
    op.add_column('article', sa.Column('celula_id', sa.Integer(), nullable=False, server_default='1'))
    op.create_foreign_key(None, 'article', 'instituicao', ['instituicao_id'], ['id'])
    op.create_foreign_key(None, 'article', 'estabelecimento', ['estabelecimento_id'], ['id'])
    op.create_foreign_key(None, 'article', 'setor', ['setor_id'], ['id'])
    op.create_foreign_key(None, 'article', 'celula', ['vis_celula_id'], ['id'])
    op.create_foreign_key('article_celula_id_fkey', 'article', 'celula', ['celula_id'], ['id'])

    op.create_table(
        'article_extra_celulas',
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('celula_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['article.id']),
        sa.ForeignKeyConstraint(['celula_id'], ['celula.id']),
        sa.PrimaryKeyConstraint('article_id', 'celula_id')
    )
    op.create_table(
        'article_extra_users',
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['article.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('article_id', 'user_id')
    )


def downgrade():
    op.drop_table('article_extra_users')
    op.drop_table('article_extra_celulas')
    op.drop_constraint('article_celula_id_fkey', 'article', type_='foreignkey')
    op.drop_constraint(None, 'article', type_='foreignkey')
    op.drop_constraint(None, 'article', type_='foreignkey')
    op.drop_constraint(None, 'article', type_='foreignkey')
    op.drop_constraint(None, 'article', type_='foreignkey')
    op.drop_column('article', 'celula_id')
    op.drop_column('article', 'vis_celula_id')
    op.drop_column('article', 'setor_id')
    op.drop_column('article', 'estabelecimento_id')
    op.drop_column('article', 'instituicao_id')
    op.drop_column('article', 'visibility')
