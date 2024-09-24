#!/usr/bin/env python

import argparse
import json
import sys


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('xcfour', help='Parsed CFOUR output in JSON.')
    parser.add_argument('-x', '--xyz', default=False, action='store_true')
    parser.add_argument('-d', '--no_dummy', default=False, action='store_true',
                        help="Do not print dummy atoms")
    args = parser.parse_args()
    return args


def distance_AU_to_A(mol_c4):
    au2A = 0.529177  # from Google, TODO: find more authorative version
    mol_xyz = mol_c4.copy()
    for atom in mol_xyz:
        atom['Coordinates'] = [pos * au2A for pos in atom['Coordinates']]
    return mol_xyz


def trim_non_atoms(mol):
    return [atom for atom in mol if atom['Z-matrix Symbol'] not in ['X', 'GH']]


def print_xyz_geometry(geometry):
    mol_xyz = distance_AU_to_A(geometry['geometry a.u.'])

    # First line of xyz file has to list number of atoms presnt in the moleucle
    print(len(mol_xyz))
    # Second line of xyz filetype is saved for a comment
    print(f"QCOMP from lines {geometry['output lines']}")
    for atom in mol_xyz:
        print(f"{atom['Z-matrix Symbol']:2s}", end='')
        for i in atom['Coordinates']:
            print(f" {i:-12.6f}", end='')
        print("")


def get_all_geometries(cfour):
    """
    Returns a list. One geometry for every xjoda section that lists the
    computational geometry (QCOMP) section.

    Example of the geometry object:
    ```
    {
      "output lines": "1234 – 1240",
      "geometry a.u.": [
        { "Z-matrix Symbol": "X",
          "Atomic Number": 0,
          "Coordinates": [ -0, -1.88972729, -3.33567616 ]
        },
        {
          "Z-matrix Symbol": "C",
          "Atomic Number": 6,
          "Coordinates": [ 2.28377565, 0, -4.6499432 ]
        },
        {
          "Z-matrix Symbol": "C",
          "Atomic Number": 6,
          "Coordinates": [ 0, 0, -6.00133672 ]
        },
        {
          "Z-matrix Symbol": "X",
          "Atomic Number": 0,
          "Coordinates": [ -0, 1.88972729, -3.33567616 ]
        },
        {
          "Z-matrix Symbol": "C",
          "Atomic Number": 6,
          "Coordinates": [ -2.28377565, 0, -4.6499432 ]
        },
        {
          "Z-matrix Symbol": "O",
          "Atomic Number": 8,
          "Coordinates": [ -0, 0, 1.89970059 ]
        },
      ]
    ```
    """
    # A single CFOUR job can list more than one geometry, e.g., optimization
    geometries = list()
    for program in cfour:
        if program['name'] != 'xjoda':
            continue

        exit_code = program['data']['exit status']
        if exit_code != 0:
            print(f"Warning: xjoda finished with exit code {exit_code}",
                  file=sys.stderr)

        for section in program['sections']:
            if section['name'] == 'qcomp':
                geometries += [{
                    'geometry a.u.': section['data']['geometry a.u.'],
                    'output lines': f"{section['start']} – {section['end']}",
                }]
                continue

    return geometries


def trim_dummy_atoms(geo):
    xyz = geo["geometry a.u."]
    new_xyz = [atom for atom in xyz if atom['Z-matrix Symbol'] != 'X']
    geo["geometry a.u."] = new_xyz


def main():
    args = get_args()
    with open(args.xcfour, 'r') as cfour_json:
        cfour = json.load(cfour_json)

    geometries = get_all_geometries(cfour)
    if len(geometries) == 0:
        print("Warning: no geometries detected in the output file.",
              file=sys.stderr)
        sys.exit(1)

    if args.xyz is True:
        for geo in geometries:
            if args.no_dummy is True:
                trim_dummy_atoms(geo)
            print_xyz_geometry(geo)


if __name__ == "__main__":
    main()
