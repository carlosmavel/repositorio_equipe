"""add cascade on article history fks

Revision ID: 2aa4d61d9b20
Revises: 8c4d2e1f9a77
Create Date: 2026-04-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2aa4d61d9b20'
down_revision = '8c4d2e1f9a77'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('revision_request') as batch_op:
        batch_op.drop_constraint('revision_request_artigo_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'revision_request_artigo_id_fkey',
            'article',
            ['artigo_id'],
            ['id'],
            ondelete='CASCADE',
        )

    with op.batch_alter_table('comment') as batch_op:
        batch_op.drop_constraint('comment_artigo_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'comment_artigo_id_fkey',
            'article',
            ['artigo_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade():
    with op.batch_alter_table('comment') as batch_op:
        batch_op.drop_constraint('comment_artigo_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'comment_artigo_id_fkey',
            'article',
            ['artigo_id'],
            ['id'],
        )

    with op.batch_alter_table('revision_request') as batch_op:
        batch_op.drop_constraint('revision_request_artigo_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'revision_request_artigo_id_fkey',
            'article',
            ['artigo_id'],
            ['id'],
        )
