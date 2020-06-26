"""Add peer feedback tables

Revision ID: 3659d0e0eb3e
Revises: 6dd3c8494722
Create Date: 2020-06-22 17:45:01.997261

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3659d0e0eb3e'
down_revision = '6dd3c8494722'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'assignment_peer_feedback_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('time', sa.Interval(), nullable=True),
        sa.Column('auto_approved_score', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'assignment_peer_feedback_connection',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('peer_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['assignment_id'], ['Assignment.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['peer_user_id'], ['User.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['User.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assignment_id', 'user_id', 'peer_user_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('assignment_peer_feedback_connection')
    op.drop_table('assignment_peer_feedback_settings')
    # ### end Alembic commands ###
