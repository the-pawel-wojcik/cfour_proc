#!/usr/bin/env python3

import sys


def add_irrep(mo, irrep_no_to_name):
    """
CFOUR is inconsitent in printing the symmetry labels.
For some MOs the symmetry label is only partial or completely missing: e.g.
...
 32   128          -0.5445967545         -14.8192302798      B1        B1 (2)
 33   251          -0.4140357155         -11.2664839842      A2        A2 (4)
 34   205          -0.3865986432         -10.5198833293      B2        B2 (3)
 35     1           0.0000000000           0.0000000000      A1        A1 (1)
 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 36    20          -0.1948807612          -5.3029748209      A1        A1 (1)
 ...
170   166           1.3838715734          37.6570579119      B1        B1 (2)
171   232           1.3909106293          37.8486003507       2         2 (3)
 ...
176    75           1.4903345380          40.5540623022      A1        A1 (1)
177   233           1.4920006032          40.5993982375                   (3)
178    76           1.5128684595          41.1672414463      A1        A1 (1)

The self-consistency checks were commented out.
  """
    name = mo['compsymm']['name']
    no = mo['compsymm']['#']

    # if no in irrep_no_to_name:
    #     if name != irrep_no_to_name[no]:
    #         raise RuntimeError(
    #             "MOs listing shows inconsitent pairing "
    #             "between computational symmetry "
    #             f"irrep # and name: {name} and {irrep_no_to_name[no]}")
    # else:
    #     irrep_no_to_name[no] = name

    if no not in irrep_no_to_name:
        irrep_no_to_name[no] = name


def get_irrep_no_to_name(cfour):
    """
    `cfour`: parsed CFOUR's output

    Returns:
        irrep_no_to_name: a dictionary that keeps irrep's # as keys
        and returns irrep's names (str) as values.
    """

    irrep_no_to_name = dict()

    for program in cfour:
        if program['name'] == 'xvscf' or program['name'] == 'xdqcscf':
            for section in program['sections']:
                if section['name'] == 'MOs':
                    if section['metadata']['ok'] is False:
                        print("Warning: Listing of MOs contains errors. Irrep"
                              " names might be incorrect. (low risk)",
                              file=sys.stderr)
                    for mo in section['data']['occupied']:
                        add_irrep(mo, irrep_no_to_name)
                    for mo in section['data']['virtual']:
                        add_irrep(mo, irrep_no_to_name)

    return irrep_no_to_name


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour')
    args = parser.parse_args()
    with open(args.cfour) as cfour_json:
        cfour = json.load(cfour_json)
    irrep_no_to_name = get_irrep_no_to_name(cfour)
    for no, name in irrep_no_to_name.items():
        print(f"{no:2d}: {name}")


if __name__ == "__main__":
    main()
