"""
This module implements all errors and warnings for psef.

This module does not contain any error checking or handling.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

import structlog
from flask import Response, g, request

from cg_json import JSONResponse, jsonify

from .exceptions import APICodes, APIWarnings, APIException

HttpWarning = t.NewType('HttpWarning', str)  # pylint: disable=invalid-name

logger = structlog.get_logger()


def make_warning(warning_text: str, code: APIWarnings) -> HttpWarning:
    """Make a ``HttpWarning`` with the given warning and code.

    :param warning_text: The text that describes the warning.
    :param code: The warning code to associate with the warning.
    :returns: A warning with the given text and code.
    """
    return HttpWarning(
        '{:03d} CodeGrade "{}"'.format(
            code.value,
            warning_text.replace('"', '\\"'),
        )
    )


def init_app(app: t.Any) -> None:
    """Initialize the flask app by setting an error handler.

    :param app: The app to initialize
    """

    @app.errorhandler(APIException)
    def handle_api_error(error: APIException) -> Response:  # pylint: disable=unused-variable
        """Handle an :class:`APIException` by converting it to a
        :class:`flask.Response`.

        :param APIException error: The error that occurred
        :returns: A response with the JSON serialized error as content.
        :rtype: flask.Response
        """
        from . import models  # pylint: disable=import-outside-toplevel
        models.db.session.expire_all()

        response = t.cast(t.Any, jsonify(error))
        response.status_code = error.status_code
        logger.warning(
            'APIException occurred',
            api_exception=error.__to_json__(),
            exc_info=True,
        )
        return response

    # Coverage is disabled for the next to handlers as they should never
    # run. When they run there is a bug in the application so we cant really
    # test them.

    @app.errorhandler(404)
    def handle_404(_: object) -> JSONResponse[APIException]:  # pylint: disable=unused-variable; #pragma: no cover
        from . import models  # pylint: disable=import-outside-toplevel
        models.db.session.expire_all()

        logger.warning('A unknown route was requested')
        api_exp = APIException(
            'The request route was not found',
            f'The route "{request.path}" does not exist',
            APICodes.ROUTE_NOT_FOUND, 404
        )
        return jsonify(api_exp, status_code=404)

    @app.errorhandler(Exception)
    def __handle_unknown_error(
        _: Exception
    ) -> JSONResponse[APIException]:  # pragma: no cover
        """Handle an unhandled error.

        This function should never really be called, as it means our code
        contains a bug.
        """
        from . import models  # pylint: disable=import-outside-toplevel
        models.db.session.expire_all()
        logger.error(
            'Unknown exception occurred', exc_info=True, report_to_sentry=True
        )

        api_exp = APIException(
            f'Something went wrong (id: {g.request_id})', (
                'The reason for this is unknown, '
                'please contact the system administrator'
            ), APICodes.UNKOWN_ERROR, 500
        )
        return jsonify(api_exp, status_code=500)
