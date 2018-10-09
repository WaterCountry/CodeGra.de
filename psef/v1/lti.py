"""
This module implements all lti routes. Please note that a lot of these routes
are not useful for most clients as the ``/lti/launch/1`` route can only be used
by an approved LTI provider and the ``/lti/launch/2`` route can only be used
directly after a successful lti launch.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
import urllib
import datetime
import urllib.parse

import jwt
import flask
import structlog
import werkzeug

import psef.errors as errors
import psef.models as models
from psef import app
from psef.lti import LTI, CanvasLTI
from psef.models import db

from . import api
from .. import helpers

logger = structlog.get_logger()


@api.route('/lti/launch/1', methods=['POST'])
@helpers.feature_required('LTI')
def launch_lti() -> t.Any:
    """Do a LTI launch.

    .. :quickref: LTI; Do a LTI Launch.
    """
    lti = {
        'params': CanvasLTI.create_from_request(flask.request).launch_params,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
    }
    return flask.redirect(
        '{}/lti_launch/?inLTI=true&jwt={}'.format(
            app.config['EXTERNAL_URL'],
            urllib.parse.quote(
                jwt.encode(
                    lti,
                    app.config['LTI_SECRET_KEY'],
                    algorithm='HS512',
                ).decode('utf8')
            )
        )
    )


@api.route('/lti/', methods=['GET'])
def get_lti_config() -> werkzeug.wrappers.Response:
    """Get a LTI config xml for this CodeGrade instance

    :qparam str lms: The name of the LMS to get the config for. This is
        required.

    :returns: An xml that can be used as a config for the specified LMS.
    """
    helpers.ensure_keys_in_dict(flask.request.args, [('lms', str)])
    lms = flask.request.args.get('lms')
    try:
        cls = helpers.get_class_by_name(LTI, '{}LTI'.format(lms))
    except ValueError:
        raise errors.APIException(
            'The requested LMS is not supported',
            f'The LMS "{lms}" is not supported', errors.APICodes.INVALID_PARAM,
            400
        )
    res = flask.make_response(
        flask.render_template(
            'lti_canvas_config.j2',
            external_url=app.config['EXTERNAL_URL'],
            properties=cls.get_lti_properties(),
            custom_extensions=cls.get_custom_extensions(),
        )
    )
    res.headers['Content-Type'] = 'application/xml; charset=utf-8'
    return res


@api.route('/lti/launch/2', methods=['POST'])
@helpers.feature_required('LTI')
def second_phase_lti_launch() -> helpers.JSONResponse[
    t.Mapping[str, t.Union[str, models.Assignment, bool]]]:
    """Do the second part of an LTI launch.

    .. :quickref: LTI; Do the callback of a LTI launch.

    :>json string jwt_token: The JWT token that is the current LTI state. This
        token can only be acquired using the ``/lti/launch/1`` route.

    :<json assignment: The assignment that the LTI launch was for.
    :<json bool new_role_created: Was a new role created in the LTI launch.
    :<json access_token: A fresh access token for the current user. This value
        is not always available, this depends on internal state so you should
        simply check.
    :<json updated_email: The new email of the current user. This is value is
        also not always available, check!
    :raises APIException: If the given Jwt token is not valid. (INVALID_PARAM)
    """
    content = helpers.ensure_json_dict(flask.request.get_json())
    helpers.ensure_keys_in_dict(content, [('jwt_token', str)])
    jwt_token = t.cast(str, content['jwt_token'])

    try:
        launch_params = jwt.decode(
            jwt_token,
            app.config['LTI_SECRET_KEY'],
            algorithms=['HS512'],
        )['params']
    except jwt.DecodeError:
        logger.warning(
            'Invalid JWT token encountered',
            token=jwt_token,
            exc_info=True,
        )
        raise errors.APIException(
            (
                'Decoding given JWT token failed, LTI is probably '
                'not configured right. Please contact your site admin.'
            ),
            f'The decoding of "{flask.request.headers.get("Jwt")}" failed.',
            errors.APICodes.INVALID_PARAM,
            400,
        )
    lti = CanvasLTI(launch_params)

    user, new_token, updated_email = lti.ensure_lti_user()
    course = lti.get_course()
    assig = lti.get_assignment(user)
    lti.set_user_role(user)
    new_role_created = lti.set_user_course_role(user, course)
    db.session.commit()

    result: t.Mapping[str, t.Union[str, models.Assignment, bool]]
    result = {
        'assignment': assig,
        'new_role_created': new_role_created,
    }
    if new_token is not None:
        result['access_token'] = new_token
    if updated_email:
        result['updated_email'] = updated_email

    return helpers.jsonify(result)
