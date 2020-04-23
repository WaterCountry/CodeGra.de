#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only

import os
import csv
import sys
import json
from collections import OrderedDict

WARNING = """
Do not edit this enum as it is automatically generated by
"{filename}".""".format(filename=os.path.basename(__file__))

HEADER = """/**
This file contains permissions

{warning}

SPDX-License-Identifier: AGPL-3.0-only
*/

/* eslint-disable */
""".format(
    filename=os.path.basename(__file__),
    warning=WARNING,
)


def to_camel_case(value: str) -> str:
    parts = value.split('_')
    return ''.join([parts[0], *(x.capitalize() for x in parts[1:])])


def generate_value_str(perm_name: str, value: object, maker) -> str:
    name = value["short_description"].replace("'", "\\'")
    desc = value["long_description"].replace("'", "\\'")
    if value.get('warning'):
        warning = "'" + value["warning"].replace("'", "\\'") + "'"
    else:
        warning = 'null'

    return (
        f"    {to_camel_case(perm_name)}: {maker}('{perm_name}', '{name}', '{desc}', {warning}),\n"
    )


def main() -> None:
    out_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'src', 'permissions.ts')
    )
    perms_path = os.path.join(
        os.path.dirname(__file__), '..', 'seed_data', 'permissions.json'
    )

    print(f'Writing to "{out_path}"', end=' ... ')
    sys.stdout.flush()

    with open(perms_path, 'r') as f_perms, open(out_path, 'w') as out:
        perms = json.load(f_perms, object_pairs_hook=OrderedDict)
        global_perms = OrderedDict((n, d) for n, d in perms.items()
                                   if not d['course_permission'])
        course_perms = OrderedDict((n, d) for n, d in perms.items()
                                   if d['course_permission'])

        out.write(HEADER)

        out.write("export type GlobalPermissionOptions =\n")
        for idx, perm_name in enumerate(global_perms.keys()):
            out.write('    | ')
            out.write(f"'{perm_name}'")
            if idx + 1 == len(global_perms):
                out.write(';')
            out.write('\n')

        out.write('const makeGPerm = (value: GlobalPermissionOptions, name: string, description: string, warning: string | null) => ({ value, name, description, warning });')

        out.write('\nexport const GlobalPermission = {\n')
        for perm_name, value in global_perms.items():
            out.write(generate_value_str(perm_name, value, 'makeGPerm'))
        out.write("};\n")

        out.write('export type GlobalPermission = typeof GlobalPermission[keyof typeof GlobalPermission];\n')

        out.write("\nexport type CoursePermissionOptions =\n")
        for idx, perm_name in enumerate(course_perms.keys()):
            out.write('    | ')
            out.write(f"'{perm_name}'")
            if idx + 1 == len(course_perms):
                out.write(';')
            out.write('\n')

        out.write('const makeCPerm = (value: CoursePermissionOptions, name: string, description: string, warning: string | null) => ({ value, name, description, warning });')

        out.write("\nexport const CoursePermission = {\n")

        for perm_name, value in course_perms.items():
            out.write(generate_value_str(perm_name, value, 'makeCPerm'))

        out.write("};\n")

        out.write('export type CoursePermission = typeof CoursePermission[keyof typeof CoursePermission];\n')

        out.write('/* eslint-enable */\n')
    print('done!')


if __name__ == '__main__':
    main()