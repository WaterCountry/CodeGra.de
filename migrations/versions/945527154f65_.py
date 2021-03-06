"""Add unique constraint to CourseSnippet table

Revision ID: 945527154f65
Revises: bba485e5def7
Create Date: 2019-04-03 16:02:12.778320

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '945527154f65'
down_revision = 'bba485e5def7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'CourseSnippet', ['course_id', 'key'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'CourseSnippet', type_='unique')
    # ### end Alembic commands ###
