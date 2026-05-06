"""add article version table

Revision ID: b4c7d9e1f2a3
Revises: aa91c3d7e5f1
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c7d9e1f2a3'
down_revision = 'aa91c3d7e5f1'
branch_labels = None
depends_on = None


def _insert_initial_snapshots_postgresql():
    op.execute(
        sa.text(
            """
            INSERT INTO article_version (
                article_id,
                version_number,
                revision_number,
                titulo,
                texto,
                status,
                visibility,
                tipo_id,
                area_id,
                sistema_id,
                instituicao_id,
                estabelecimento_id,
                setor_id,
                vis_celula_id,
                celula_id,
                user_id_original_author,
                changed_by_user_id,
                changed_by_username,
                changed_by_email,
                changed_by_nome_completo,
                change_action,
                source_status_before,
                source_status_after,
                title_char_count,
                text_char_count,
                text_word_count,
                content_hash,
                drastic_reduction_detected,
                created_at
            )
            SELECT
                a.id,
                a.current_version_number,
                a.current_revision_number,
                a.titulo,
                a.texto,
                a.status::text,
                COALESCE(a.visibility::text, 'celula'),
                a.tipo_id,
                a.area_id,
                a.sistema_id,
                a.instituicao_id,
                a.estabelecimento_id,
                a.setor_id,
                a.vis_celula_id,
                a.celula_id,
                a.user_id,
                a.user_id,
                u.username,
                u.email,
                u.nome_completo,
                'migration_initial_snapshot',
                NULL,
                a.status::text,
                char_length(COALESCE(a.titulo, '')),
                char_length(COALESCE(a.texto, '')),
                CASE
                    WHEN btrim(COALESCE(a.texto, '')) = '' THEN 0
                    ELSE cardinality(regexp_split_to_array(btrim(a.texto), '\\s+'))
                END,
                md5(concat_ws(chr(31), COALESCE(a.titulo, ''), COALESCE(a.texto, ''), a.status::text, COALESCE(a.visibility::text, 'celula'))),
                false,
                COALESCE(a.created_at, CURRENT_TIMESTAMP)
            FROM article a
            LEFT JOIN "user" u ON u.id = a.user_id
            """
        )
    )


def _insert_initial_snapshots_generic():
    op.execute(
        sa.text(
            """
            INSERT INTO article_version (
                article_id,
                version_number,
                revision_number,
                titulo,
                texto,
                status,
                visibility,
                tipo_id,
                area_id,
                sistema_id,
                instituicao_id,
                estabelecimento_id,
                setor_id,
                vis_celula_id,
                celula_id,
                user_id_original_author,
                changed_by_user_id,
                changed_by_username,
                changed_by_email,
                changed_by_nome_completo,
                change_action,
                source_status_before,
                source_status_after,
                title_char_count,
                text_char_count,
                text_word_count,
                drastic_reduction_detected,
                created_at
            )
            SELECT
                a.id,
                a.current_version_number,
                a.current_revision_number,
                a.titulo,
                a.texto,
                a.status,
                COALESCE(a.visibility, 'celula'),
                a.tipo_id,
                a.area_id,
                a.sistema_id,
                a.instituicao_id,
                a.estabelecimento_id,
                a.setor_id,
                a.vis_celula_id,
                a.celula_id,
                a.user_id,
                a.user_id,
                u.username,
                u.email,
                u.nome_completo,
                'migration_initial_snapshot',
                NULL,
                a.status,
                length(COALESCE(a.titulo, '')),
                length(COALESCE(a.texto, '')),
                0,
                false,
                COALESCE(a.created_at, CURRENT_TIMESTAMP)
            FROM article a
            LEFT JOIN "user" u ON u.id = a.user_id
            """
        )
    )


def upgrade():
    op.add_column(
        'article',
        sa.Column('current_version_number', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'article',
        sa.Column('current_revision_number', sa.Integer(), nullable=False, server_default='1'),
    )

    op.create_table(
        'article_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('visibility', sa.String(length=32), nullable=False),
        sa.Column('tipo_id', sa.Integer(), nullable=True),
        sa.Column('area_id', sa.Integer(), nullable=True),
        sa.Column('sistema_id', sa.Integer(), nullable=True),
        sa.Column('instituicao_id', sa.Integer(), nullable=True),
        sa.Column('estabelecimento_id', sa.Integer(), nullable=True),
        sa.Column('setor_id', sa.Integer(), nullable=True),
        sa.Column('vis_celula_id', sa.Integer(), nullable=True),
        sa.Column('celula_id', sa.Integer(), nullable=True),
        sa.Column('user_id_original_author', sa.Integer(), nullable=True),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('changed_by_username', sa.String(length=80), nullable=True),
        sa.Column('changed_by_email', sa.String(length=120), nullable=True),
        sa.Column('changed_by_nome_completo', sa.String(length=255), nullable=True),
        sa.Column('change_action', sa.String(length=64), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('source_status_before', sa.String(length=32), nullable=True),
        sa.Column('source_status_after', sa.String(length=32), nullable=True),
        sa.Column('title_char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text_char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text_word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('previous_text_char_count', sa.Integer(), nullable=True),
        sa.Column('text_reduction_percent', sa.Float(), nullable=True),
        sa.Column('drastic_reduction_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('correlation_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['article_id'], ['article.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_article_version_article_id', 'article_version', ['article_id'], unique=False)
    op.create_index(
        'ix_article_version_article_version_revision',
        'article_version',
        ['article_id', 'version_number', 'revision_number'],
        unique=False,
    )
    op.create_index('ix_article_version_created_at', 'article_version', ['created_at'], unique=False)
    op.create_index('ix_article_version_changed_by_user_id', 'article_version', ['changed_by_user_id'], unique=False)

    op.execute(
        sa.text(
            """
            UPDATE article
            SET current_version_number = CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END,
                current_revision_number = CASE WHEN status = 'aprovado' THEN 0 ELSE 1 END
            """
        )
    )

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        _insert_initial_snapshots_postgresql()
    else:
        _insert_initial_snapshots_generic()


def downgrade():
    op.drop_index('ix_article_version_changed_by_user_id', table_name='article_version')
    op.drop_index('ix_article_version_created_at', table_name='article_version')
    op.drop_index('ix_article_version_article_version_revision', table_name='article_version')
    op.drop_index('ix_article_version_article_id', table_name='article_version')
    op.drop_table('article_version')
    op.drop_column('article', 'current_revision_number')
    op.drop_column('article', 'current_version_number')
