"""Initial schema: create all tables and types"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1) cria o ENUM article_status
    op.execute("""
        CREATE TYPE article_status AS ENUM (
          'rascunho',
          'pendente',
          'em_revisao',
          'em_ajuste',
          'aprovado',
          'rejeitado'
        );
    """)

    # 2) cria a tabela user
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(80), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('nome_completo', sa.String(255), nullable=True),
        sa.Column('foto', sa.String(255), nullable=True),
    )

    # 3) cria a tabela article
    op.create_table(
        'article',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('titulo', sa.String(200), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum(
            'rascunho','pendente','em_revisao','em_ajuste','aprovado','rejeitado',
             name='article_status',
             native_enum=False
        ), nullable=False, server_default='rascunho'),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('arquivos', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 4) cria a tabela revision_request
    op.create_table(
        'revision_request',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('artigo_id', sa.Integer(), sa.ForeignKey('article.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('comentario', sa.Text(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # 5) cria a tabela notification
    op.create_table(
        'notification',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('message', sa.String(255), nullable=False),
        sa.Column('url', sa.String(255), nullable=True),
        sa.Column('lido', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )


def downgrade():
    op.drop_table('notification')
    op.drop_table('revision_request')
    op.drop_table('article')
    op.drop_table('user')
    op.execute('DROP TYPE article_status;')