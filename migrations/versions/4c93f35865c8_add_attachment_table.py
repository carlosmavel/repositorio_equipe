"""Add Attachment table

Revision ID: 4c93f35865c8
Revises: 67ef260f5a21
Create Date: 2025-05-27 09:27:50.322986

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4c93f35865c8'
down_revision = '67ef260f5a21'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Cria a tabela attachment
    op.create_table(
        'attachment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('article.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    # 2) Índice GIN para busca full-text no content
    op.execute(
        "CREATE INDEX ix_attachment_content_fts "
        "ON attachment USING GIN(to_tsvector('portuguese', content));"
    )

    # Ajustes herdados da migração anterior
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=postgresql.ENUM(
                   'rascunho','pendente','em_revisao','em_ajuste','aprovado','rejeitado',
                   name='article_status'),
               type_=sa.Enum(
                   'rascunho','pendente','em_revisao','em_ajuste','aprovado','rejeitado',
                   name='article_status', native_enum=False),
               existing_nullable=False,
               existing_server_default=sa.text("'rascunho'::article_status")
        )
    
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('user')}

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'nome_completo',
            existing_type=sa.VARCHAR(length=120),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'foto',
            existing_type=sa.VARCHAR(length=200),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        if 'cargo' in columns:
            batch_op.drop_column('cargo')
        if 'setor' in columns:
            batch_op.drop_column('setor')


def downgrade():
    # 1) Remove índice e tabela attachment
    op.execute("DROP INDEX ix_attachment_content_fts;")
    op.drop_table('attachment')

    # 2) Reverte ajustes de user
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('setor', sa.VARCHAR(length=80), nullable=True))
        batch_op.add_column(sa.Column('cargo', sa.VARCHAR(length=80), nullable=True))
        batch_op.alter_column('foto',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=200),
               existing_nullable=True
        )
        batch_op.alter_column('nome_completo',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=120),
               existing_nullable=True
        )

    # 3) Reverte ajuste na article.status
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=sa.Enum(
                   'rascunho','pendente','em_revisao','em_ajuste','aprovado','rejeitado',
                   name='article_status', native_enum=False),
               type_=postgresql.ENUM(
                   'rascunho','pendente','em_revisao','em_ajuste','aprovado','rejeitado',
                   name='article_status'),
               existing_nullable=False,
               existing_server_default=sa.text("'rascunho'::article_status")
        )

    # ### end Alembic commands ###