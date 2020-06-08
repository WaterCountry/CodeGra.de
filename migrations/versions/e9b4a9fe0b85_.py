"""Add link table between course and lti provider

Revision ID: e9b4a9fe0b85
Revises: 0a54c07d27ea
Create Date: 2020-02-06 15:28:27.942673

"""
import uuid

import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op
from sqlalchemy.sql import text

import cg_dt_utils

# revision identifiers, used by Alembic.
revision = 'e9b4a9fe0b85'
down_revision = '0a54c07d27ea'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'course_lti_provider',
        sa.Column(
            'id', sqlalchemy_utils.types.uuid.UUIDType(), nullable=False
        ),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('lti_provider_id', sa.String(length=36), nullable=False),
        sa.Column('lti_course_id', sa.Unicode(), nullable=False),
        sa.Column('deployment_id', sa.Unicode(), nullable=False),
        sa.ForeignKeyConstraint(
            ['course_id'],
            ['Course.id'],
        ), sa.ForeignKeyConstraint(
            ['lti_provider_id'],
            ['LTIProvider.id'],
        ), sa.PrimaryKeyConstraint('id'), sa.UniqueConstraint('course_id'),
        sa.UniqueConstraint(
            'lti_provider_id', 'deployment_id', 'lti_course_id'
        )
    )

    conn = op.get_bind()
    lti_courses = conn.execute(
        text(
            'SELECT id, lti_provider_id, lti_course_id FROM "Course" WHERE'
            ' lti_course_id IS NOT NULL'
        )
    )
    for course_id, lti_provider_id, lti_course_id in lti_courses:
        now = cg_dt_utils.DatetimeWithTimezone.utcnow()
        conn.execute(
            text(
                'INSERT INTO course_lti_provider '
                '(id, created_at, updated_at, course_id, lti_provider_id,'
                ' lti_course_id, deployment_id)'
                ' VALUES '
                '(:pk, :created_at, :updated_at, :course_id, :lti_provider_id,'
                ' :lti_course_id, :deployment_id)'
            ),
            pk=uuid.uuid4(),
            created_at=now,
            updated_at=now,
            course_id=course_id,
            lti_provider_id=lti_provider_id,
            lti_course_id=lti_course_id,
            deployment_id=lti_course_id,
        )

    op.drop_constraint('Course_lti_course_id_key', 'Course', type_='unique')
    op.drop_constraint(
        'Course_lti_provider_id_fkey', 'Course', type_='foreignkey'
    )
    op.drop_column('Course', 'lti_course_id')
    op.drop_column('Course', 'lti_provider_id')
    op.create_unique_constraint(
        'LTIProvider_client_id_key_key', 'LTIProvider', ['client_id', 'key']
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        'LTIProvider_client_id_key_key', 'LTIProvider', type_='unique'
    )
    op.add_column(
        'Course',
        sa.Column(
            'lti_provider_id',
            sa.VARCHAR(length=36),
            autoincrement=False,
            nullable=True
        )
    )
    op.add_column(
        'Course',
        sa.Column(
            'lti_course_id', sa.VARCHAR(), autoincrement=False, nullable=True
        )
    )
    op.create_foreign_key(
        'Course_lti_provider_id_fkey', 'Course', 'LTIProvider',
        ['lti_provider_id'], ['id']
    )
    op.create_unique_constraint(
        'Course_lti_course_id_key', 'Course', ['lti_course_id']
    )

    conn = op.get_bind()
    course_lti_provider = conn.execute(
        text(
            'SELECT course_id, lti_provider_id, lti_course_id, deployment_id'
            ' FROM course_lti_provider'
        )
    )
    for (
        course_id, lti_provider_id, lti_course_id, deployment_id
    ) in course_lti_provider:
        assert lti_course_id == deployment_id, 'Unsupported downgrade'
        conn.execute(
            text(
                'UPDATE "Course" SET lti_provider_id = :prov_id,'
                ' lti_course_id = :lti_course_id WHERE id = :course_id'
            ),
            course_id=course_id,
            lti_course_id=lti_course_id,
            prov_id=lti_provider_id,
        )

    op.drop_table('course_lti_provider')
    # ### end Alembic commands ###
