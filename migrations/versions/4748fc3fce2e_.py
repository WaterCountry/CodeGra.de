"""Add columns for submission limitting

Revision ID: 4748fc3fce2e
Revises: 0a6c16ad4847de44317e
Create Date: 2020-01-06 18:12:32.411133

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '4748fc3fce2e'
down_revision = '0a6c16ad4847de44317e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Assignment', sa.Column('cool_off_period', sa.Interval(), nullable=True))
    op.add_column('Assignment', sa.Column('max_amount_of_submissions', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Assignment', 'max_amount_of_submissions')
    op.drop_column('Assignment', 'cool_off_period')
    # ### end Alembic commands ###
