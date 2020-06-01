import copy
import uuid

import jwt
import furl
import pytest

import helpers
import psef.models as m
import psef.signals as signals
import psef.lti.v1_3 as lti1p3

LTI_JWT_SECRET = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def monkeypatch_get_members(monkeypatch, stub_function_class):
    stub = stub_function_class(lambda: [])
    monkeypatch.setattr(m.CourseLTIProvider, 'get_members', stub)
    yield stub


@pytest.fixture(autouse=True)
def monkeypatch_validate_jwt(monkeypatch, stub_function_class):
    stub = stub_function_class(
        lambda self: self, pass_self=True, with_args=True
    )
    monkeypatch.setattr(lti1p3.MessageLaunch, 'validate_jwt_signature', stub)
    yield stub


def merge(d1, d2):
    res = copy.copy(d1)

    for k, v2 in d2.items():
        v1 = d1.get(k)
        if isinstance(v1, dict) and isinstance(v2, dict):
            res[k] = merge(v1, v2)
        else:
            res[k] = v2

    return res


def replace_values(base_data, replace_dict):
    if isinstance(base_data, list):
        return [replace_values(item, replace_dict) for item in base_data]
    elif isinstance(base_data, dict):
        res = {}
        for key, value in base_data.items():
            if isinstance(value, list):
                res[key] = replace_values(value, replace_dict)
            elif isinstance(value, dict):
                res[key] = replace_values(value, replace_dict)
            elif value in replace_dict:
                res[key] = replace_dict[value]
            else:
                res[key] = value
        return res
    elif base_data in replace_dict:
        return replace_dict[base_data]
    return copy.copy(base_data)


BASE_LAUNCH_DATA = {
    'aud': 'client_id',
    'exp': 1590999956,
    'nbf': 1590998156,
    'iat': 1590998156,
    'sub': '91f41e6b-a507-4168-9347-204b9316f03d_6324',
    'given_name': 'CodeGrade',
    'family_name': 'Administrator',
    'name': 'CodeGrade Administrator',
    'email': 'User@email.com',
    'https://purl.imsglobal.org/spec/lti/claim/message_type':
        'LtiResourceLinkRequest',
    'https://purl.imsglobal.org/spec/lti/claim/version': '1.3.0',
    'https://purl.imsglobal.org/spec/lti/claim/deployment_id': 'Deployment.id',
    'https://purl.imsglobal.org/spec/lti/claim/target_link_uri': 'Launch.url',
    'https://purl.imsglobal.org/spec/lti/claim/resource_link': {
        'id': 'Assignment.id',
        'title': 'Assignment.name',
        'description': None,
    },
    'https://purl.imsglobal.org/spec/lti/claim/roles': [
        'http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Student',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Learner',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Mentor',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Staff',
        'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator',
    ],
    'https://purl.imsglobal.org/spec/lti/claim/context': {
        'id': 'Course.id',
        'label': 'Course.label',
        'title': 'Course.title',
        'type': [
            'http://purl.imsglobal.org/vocab/lis/v2/course#CourseOffering',
        ],
    },
    'https://purl.imsglobal.org/spec/lti/claim/lis': {
        'course_offering_sourcedid': 'partners.brightspace.com:CodeGrade1',
        'course_section_sourcedid': 'partners.brightspace.com:CodeGrade1',
    },
    'https://purl.imsglobal.org/spec/lti/claim/launch_presentation': {
        'locale': 'en-us',
    },
    'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint': {
        'scope': [
            'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
            'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly',
            'https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly',
            'https://purl.imsglobal.org/spec/lti-ags/scope/score',
        ],
        'lineitems': 'lineitems.endpoint',
    },
    'https://purl.imsglobal.org/spec/lti/claim/custom': {
        'cg_username_0': 'cg_username',
        'cg_deadline_0': 'cg_deadline',
        'cg_available_at_0': 'cg_available_at',
        'cg_resource_id_0': 'cg_resource_id',
        'cg_lock_date_0': 'cg_lock_date',
    },
    'https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice': {
        'context_memberships_url': 'context_memberships_url',
        'service_versions': ['2.0'],
    },
}

CANVAS_DATA = merge(
    BASE_LAUNCH_DATA, {
        'iss': 'https://canvas.instructure.com',
        'https://purl.imsglobal.org/spec/lti/claim/custom': {
            'cg_deadline_1': 'cg_deadline',
            'cg_is_published_0': 'cg_is_published',
            'cg_resource_id_1': 'cg_resource_id',
            'cg_lock_date_1': 'cg_lock_date',
        }
    }
)

BRIGHTSPACE_DATA = merge(
    BASE_LAUNCH_DATA,
    {
        'iss': 'https://partners.brightspace.com',
        'http://www.brightspace.com': {
            'tenant_id': '41b632b6-ff74-4288-b3f1-7ffb6eb14bb4',
            'org_defined_id': 'CodeGrade.A1',
            'user_id': 'User.id',
            'username': 'User.username',
            'ResourceLink.id.history': '',
            'Context.id.history': '',
        },
    },
)


def make_launch_data(base, provider, override_replace={}):
    provider = m.LTI1p3Provider.query.get(helpers.get_id(provider))

    return replace_values(
        base,
        {
            'cg_username': 'Test username',
            'cg_deadline': '',
            'cg_available_at': '',
            'cg_resource_id': '',
            'cg_lock_date': '',
            'Assignment.name': 'Test Assignment 1',
            'Course.label': 'Test Course 1',
            'Course.id': str(uuid.uuid4()),
            'User.id': str(uuid.uuid4()),
            'User.username': 'Test username',
            'Assignment.id': str(uuid.uuid4()),
            'iss': provider.iss,
            'client_id': provider.client_id,
            **override_replace,
        },
    )


def do_oidc_login(test_client, provider, with_id=False):
    provider = m.LTI1p3Provider.query.get(helpers.get_id(provider))

    redirect_uri = str(uuid.uuid4())
    login_hint = str(uuid.uuid4())
    url = '/api/v1/lti1.3/login'
    if with_id:
        url += '/' + str(provider.id)

    redirect = test_client.post(
        url,
        data={
            'target_link_uri': redirect_uri,
            'iss': provider.iss,
            'client_id': provider.client_id,
            'login_hint': login_hint,
        }
    )
    assert redirect.status_code == 303
    assert redirect.headers['Location'].startswith(provider._auth_login_url)
    return furl.furl(redirect.headers['Location']).asdict()


def do_lti_launch(
    test_client, provider, data, oidc_result, status, with_id=False
):
    oidc_params = dict(oidc_result['query']['params'])
    url = '/api/v1/lti1.3/launch'
    if with_id:
        url += '/' + str(provider.id)
    response = test_client.post(
        url,
        data={
            'id_token':
                jwt.encode(
                    {**data, 'nonce': oidc_params['nonce']},
                    LTI_JWT_SECRET,
                    algorithm='HS256',
                ),
            'state': oidc_params['state'],
        },
    )
    assert response.status_code == 303
    url = furl.furl(response.headers['Location'])
    blob_id = dict(url.asdict()['query']['params'])['blob_id']
    return test_client.req(
        'post',
        '/api/v1/lti/launch/2?extended',
        status,
        data={
            'blob_id': blob_id,
        }
    )


def do_oidc_and_lti_launch(
    test_client, provider, data, status=200, with_id=False
):
    oidc = do_oidc_login(test_client, provider, with_id=with_id)
    launch = do_lti_launch(test_client, provider, data, oidc, status, with_id)
    return oidc, launch


def make_provider(
    test_client,
    lms,
    iss=None,
    client_id=None,
    auth_token_url=None,
    auth_login_url=None,
    key_set_url=None,
    auth_audience=None
):
    prov = test_client.req(
        'post',
        '/api/v1/lti1.3/providers/',
        200,
        data={
            'lms': lms,
            'iss': iss or str(uuid.uuid4()),
            'intended_use': 'A test provider',
        }
    )

    def make_data(**data):
        return {k: v or 'http://' + str(uuid.uuid4()) for k, v in data.items()}

    return test_client.req(
        'patch',
        f'/api/v1/lti1.3/providers/{helpers.get_id(prov)}',
        200,
        data=make_data(
            client_id=client_id,
            auth_token_url=auth_token_url,
            auth_login_url=auth_login_url,
            auth_audience=auth_audience,
            key_set_url=key_set_url,
            finalize=True,
        )
    )


@pytest.mark.parametrize(
    'launch_data,lms,iss', [
        (BRIGHTSPACE_DATA, 'Brightspace', 'https://partners.brightspace.com'),
        (CANVAS_DATA, 'Canvas', 'https://canvas.instructure.com'),
    ]
)
def test_do_simple_launch(
    test_client, describe, logged_in, admin_user, watch_signal,
    monkeypatch_validate_jwt, launch_data, lms, iss
):
    with describe('setup'), logged_in(admin_user):
        provider = make_provider(
            test_client,
            lms,
            iss=iss,
            client_id=str(uuid.uuid4()) + '_lms=' + lms
        )
        assig_created = watch_signal(signals.ASSIGNMENT_CREATED)

    with describe('Simple launch'):
        lti_assig_id = str(uuid.uuid4())
        oidc, launch = do_oidc_and_lti_launch(
            test_client, provider,
            make_launch_data(
                launch_data,
                provider,
                {
                    'Assignment.id': lti_assig_id,
                },
            )
        )
        assert monkeypatch_validate_jwt.called_amount == 1

        assert assig_created.was_send_once
        assert assig_created.signal_arg.lti_assignment_id == lti_assig_id
