#!/usr/bin/env python3

import argparse
import json
import sys
from geometry import get_all_geometries, distance_AU_to_A, trim_non_atoms


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_file', help='Parsed CFOUR output.')
    parser.add_argument('-j', '--json', default=False, action='store_true',
                        help="Print normal coordinates gradient in json.")
    parser.add_argument('-M', '--Mulliken', default=False, action='store_true',
                        help="Print mode's number using the Mulliken's"
                        " convention. Available only for D2h point group.")
    parser.add_argument('-v', '--verbose', default=0, action='count',
                        help="Print summary to the standard output.")
    parser.add_argument('-x', '--xyz', default=False, action='store_true',
                        help="Print normal coordinates in the xyz format (jmol"
                             " can display it). Geometry in Å, mode in"
                        " dimensionless normal coordinates.")
    args = parser.parse_args()
    return args


def collect_point_group(cfour) -> str:
    """
    Extracts normal coordinates.

    Returns:
        point_group (str): Computational point group listed in the first xjoda.
        Returns empty string if error.
    """
    first_xjoda = None

    for program in cfour:
        if program['name'] == 'xjoda':
            first_xjoda = program
            break

    if first_xjoda is None:
        print("Error: xjoda section is missing. Cannot get point group.",
              file=sys.stderr)
        return ""

    point_group = None
    for section in first_xjoda['sections']:
        if section['name'] != 'point group':
            continue

        if section['metadata']['ok'] is False:
            print("Error: Point group section of xjoda is corrupted."
                  "Point group might be invalid.",
                  file=sys.stderr)

        data = section['data']
        if 'computational point group' in data:
            point_group = data['computational point group']

    if point_group is None:
        print("Error: Cannot collect the point group from xjoda.",
              file=sys.stderr)
        point_group = ""

    return point_group


def collect_normal_coordinates(cfour):
    """
    Extracts normal coordinates.

    Returns:
        normal_coordinates: list()
    """
    last_xjoda = None

    for program in cfour:
        if program['name'] == 'xjoda':
            last_xjoda = program

    normal_coordinates = None
    for section in last_xjoda['sections']:
        if section['name'] != 'normal coordinates':
            continue

        if 'normal coordinates' not in section['data']:
            print("Error: Normal coordinates of xjoda is missing data.",
                  file=sys.stderr)
            return []

        normal_coordinates = section['data']['normal coordinates']

    if normal_coordinates is None:
        print("Warrning: Normal coordinates missing in xjoda.",
              file=sys.stderr)

    return normal_coordinates


def xsim_input_normal_coordinates(normal_coordinates):
    """
    Change the formating of the 'coordinate' part of every entry.
    """

    xsim_ncs = []
    for normal_coordinate in normal_coordinates:
        coordinate = [[nc['x'], nc['y'], nc['z']]
                      for nc in normal_coordinate['coordinate']]
        xsim_ncs += [{
            'symmetry': normal_coordinate['symmetry'],
            'frequency, cm-1': normal_coordinate['frequency, cm-1'],
            'kind': normal_coordinate['kind'],
            'coordinate': coordinate,
        }]

    return xsim_ncs


def sort_Mulliken(point_group, mode):
    if point_group.lower() == "d2h":
        return (mode['symmetry'], -mode['frequency, cm-1'])
        # return mode['symmetry']

    return 0


def verbose_print(args, point_group: str, normal_coordinates) -> None:
    print(f"Computational point group: {point_group}")
    print("Normal Coordinates:")
    for id, mode in enumerate(normal_coordinates):
        print_id = id
        if args.Mulliken is True:
            print_id += 1
        print(f"{print_id:>3d}:"
              f" {mode['symmetry']:3}"
              f" {mode['kind'].title()},"
              f"{mode['frequency, cm-1']:-8.2f}")
        if args.verbose > 1:
            for xyz in mode['coordinate']:
                print(f"{xyz['atomic symbol']:>3s} ", end='')
                for idx in ['x', 'y', 'z']:
                    print(f" {xyz[idx]:-7.4f}", end='')
                print("")


def main():
    args = get_args()
    with open(args.cfour_file, 'r') as cfour_file_input:
        cfour = json.load(cfour_file_input)

    point_group = collect_point_group(cfour)
    normal_coordinates = collect_normal_coordinates(cfour)

    if args.Mulliken is True:
        normal_coordinates.sort(key=lambda x: sort_Mulliken(point_group, x))
        for mode in normal_coordinates:
            mode['symmetry'] = mode['symmetry'].lower()

    if args.json is True:
        xsim_ncs = xsim_input_normal_coordinates(normal_coordinates)
        print(json.dumps(xsim_ncs))

    if args.verbose > 0:
        verbose_print(args, point_group, normal_coordinates)

    if args.xyz is True:

        geo_au = get_all_geometries(cfour)[0]['geometry a.u.']
        geo = distance_AU_to_A(geo_au)
        geo = trim_non_atoms(geo)

        for id, mode in enumerate(normal_coordinates):
            print_id = id
            if args.Mulliken is True:
                print_id += 1

            print(len(geo))
            comment = f"{str(print_id):>3s}. "
            comment += f"{mode['kind'].title()} mode, "
            comment += f"{mode['frequency, cm-1']} cm-1, "
            comment += f"{mode['symmetry']}"
            print(comment)

            for xyz, vib in zip(geo, mode['coordinate']):
                atom_symbol = xyz['Z-matrix Symbol']
                if atom_symbol != vib['atomic symbol']:
                    print(f"Warning! Mismatch between the geometry atoms order"
                          f"and the vibrational atoms order in {atom_symbol}"
                          f"and {vib['atomic symbol']}.", file=sys.stderr)

                print(f"{atom_symbol:2}", end='')
                for pos in xyz['Coordinates']:
                    print(f" {pos:-9.6f}", end='')
                for idx in ['x', 'y', 'z']:
                    print(f" {vib[idx]:-8.5f}", end='')
                print("")


if __name__ == "__main__":
    main()
