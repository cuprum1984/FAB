"""add last_seen_at to group_topics

Revision ID: 88a00f1d5104
Revises: c8eb4f8face9
Create Date: 2026-02-23 10:42:27.741103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88a00f1d5104'
down_revision: Union[str, Sequence[str], None] = 'c8eb4f8face9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле last_seen_at в таблицу group_topics
    op.add_column('group_topics', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    
    # Создаём индекс для оптимизации запросов по last_seen_at
    op.create_index('idx_topic_last_seen', 'group_topics', ['last_seen_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индекс
    op.drop_index('idx_topic_last_seen', table_name='group_topics')
    
    # Удаляем поле last_seen_at
    op.drop_column('group_topics', 'last_seen_at')
