"""Add deleted flag to assignments

Revision ID: 0ab8d5e2eab2
Revises: a1cac0cb62ca
Create Date: 2019-12-12 15:02:05.673800

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '0ab8d5e2eab2'
down_revision = 'a1cac0cb62ca'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Assignment', sa.Column('deleted', sa.Boolean(), server_default='false', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Assignment', 'deleted')
    # ### end Alembic commands ###
