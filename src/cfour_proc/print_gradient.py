#!/usr/bin/env python3

import argparse
import json
import sys
from print_roots import collect_eom_roots_xncc
from print_roots_xvee import collect_eom_roots_xvee


# Only terms in the root with amplitude larger than this values will get
# printed. If the threshold is set too small, then amplitudes with large MO #
# appear -- leading to difficulties in comparison between different basis sets.
SINGLE_THRESHOLD = 0.1
DOUBLE_THRESHOLD = 0.1


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_file', help='A parsed CFOUR file')
    parser.add_argument('-j', '--json', default=False, action='store_true',
                        help="Print normal coordinates gradient in json.")
    parser.add_argument('-v', '--verbose', default=0, action='count',
                        help="Print a summary to stdandard output.")
    args = parser.parse_args()
    return args


# Deprecated
# def collect_eom_roots(cfour):
#     """
#     Extracts EOM roots data from parsed CFOUR's output.

#     Returns:
#         roots: list()
#     """
#     roots = []

#     for xvee in cfour:
#         if xvee['name'] != 'xvee':
#             continue
#         for solution in xvee['sections']:
#             if solution['name'] != 'eom solution':
#                 continue

#             # TODO: make it part of a separate module
#             if solution['metadata']['ok'] is False:
#                 if 'start' in solution:
#                     start = solution['start']
#                 else:
#                     start = 0

#                 if 'end' in solution:
#                     end = solution['end']
#                 else:
#                     end = -1

#                 print("Warning: Cannot read from an ivalid section "
#                       f"{solution['name']} (lines {start}-{end}).",
#                       file=sys.stderr)
#                 continue

#             eom_model = solution['data']['model']
#             root_energy = solution['data']['energy']
#             irrep = solution['data']['irrep']

#             roots += [{
#                 'model': eom_model,
#                 'irrep': irrep,
#                 'energy': root_energy,
#             }]
#         break

#     return roots


def collect_gradient(cfour):
    """
    Extracts normal coordinate gradient.

    Returns:
        gradient: list()
    """
    last_xjoda = None

    for program in cfour:
        if program['name'] == 'xjoda':
            last_xjoda = program

    gradient = list()
    for section in last_xjoda['sections']:
        if section['name'] != 'normal coordinate gradient':
            continue

        if 'Normal Coordinate Gradient' not in section['data']:
            print("Error: Normal coordinate gradient missing in xjoda.",
                  file=sys.stderr)
            return []

        for component in section['data']['Normal Coordinate Gradient']:
            gradient += [{
                'mode #': component['mode #'],
                'frequency, cm-1': component['omega'],
                'gradient, cm-1': component['dE/dQ, cm-1'],
                }]

    return gradient


def main():
    args = get_args()
    with open(args.cfour_file, 'r') as cfour_file_input:
        cfour = json.load(cfour_file_input)

    xncc_roots = collect_eom_roots_xncc(cfour)
    xvee_roots = collect_eom_roots_xvee(cfour)
    if len(xncc_roots) == 0 and len(xvee_roots) == 0:
        print("Warning: No EOM roots detected in the gradient calculation",
              file=sys.stderr)
    roots = xncc_roots + xvee_roots

    gradient = collect_gradient(cfour)
    outpack = {
        'gradient': gradient,
        'EOM states': roots,
    }

    if args.json is True:
        print(json.dumps(outpack))

    if args.verbose > 0:
        print("EOM root(s) related to the gradient:")
        for state in outpack['EOM states']:
            print(state)
        print("The normal coordinate gradient components:")
        for component in outpack['gradient']:
            print(component)


if __name__ == "__main__":
    main()
