#!/usr/bin/env python3

import argparse
import json
import sys
from cfour_proc.irrep_no_to_name import get_irrep_no_to_name


# Only terms in the root with amplitude larger than this values will get
# printed. If the threshold is set too small, then amplitudes with large MO #
# apear -- leading to difficulties in comparison between different basis sets.
SINGLE_THRESHOLD = 0.1
DOUBLE_THRESHOLD = 0.1


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cfour_file', help='A parsed CFOUR file')
    parser.add_argument('-c', '--cbs', default=False, action='store_true',
                        help='Print EOM roots as an input for a CBS fitting.')
    parser.add_argument('-e', '--excite', default=False, action='store_true',
                        help="Print EOM roots as in the extra excite section.")
    parser.add_argument('-j', '--json', default=False, action='store_true',
                        help="Print EOM roots as json.")
    parser.add_argument('-s', '--summary', default=0, action='count',
                        help="Print a summary of EOM roots.")
    args = parser.parse_args()
    return args


def get_basis(cfour):
    """ Extracts basis name from parsed CFOUR's output.

    Returns:
    `basis`: a string represting the used basis set, in the same format as it
            appears in the CFOUR's listing of the control parameters
    """

    for xjoda in cfour:
        if xjoda['name'] == 'xjoda':
            break

    if xjoda['name'] != 'xjoda':
        print("Warning xjoda section missing.", file=sys.stderr)
        return

    for control_parameters in xjoda['sections']:
        if control_parameters['name'] == 'control parameters':
            break

    if control_parameters['name'] != 'control parameters':
        print("Warning control parameters section missing.", file=sys.stderr)
        return

    raw_basis = control_parameters['data']['BASIS']['value']
    basis = raw_basis.split()[0]

    return basis


def add_irrep_energy_no_and_name(roots: list, cfour):
    """
    Using the SCF listing add translation from the irrep number that CFOUR uses
    to the irrep name (e.g. Ag, or B3u).

    Additionally add the `energy #` keyword to each irrep. This number orders
    the states by their energy, but there is a separate counter for each irrep.
    """
    irrep_no_to_name = get_irrep_no_to_name(cfour)

    roots.sort(key=lambda x: x['energy']['total']['au'])
    energy_irrep = dict()
    for root in roots:
        irrep = root['irrep']
        number = irrep['#']
        name = irrep_no_to_name[number]
        irrep['name'] = name
        if number in energy_irrep:
            energy_irrep[number] += 1
        else:
            energy_irrep[number] = 1
        irrep['energy #'] = energy_irrep[number]


def get_scf_energy(cfour):
    """ Extracts SCF energy from parsed CFOUR's output.

    Returns:
        `scf`: float() the SCF energy in au
    """

    for scf_program in cfour:
        if scf_program['name'] == 'xvscf' or scf_program['name'] == 'xdqcscf':
            break

    if scf_program['name'] != 'xvscf' and scf_program['name'] != 'xdqcscf':
        print("Warning SCF program missing. Cannot extract SCF energy",
              file=sys.stderr)
        return

    return scf_program['data']['energy']['au']


def get_cc_data(cfour):
    """ Extracts CC data from parsed CFOUR's output.

    Returns:
        `cc`: a dictionary with coupled cluster data
                "calclevel": CCSD|CCSDT|CCSDTQ
                "cc_energy": total CC energy in au
    """

    for xncc in cfour:
        if xncc['name'] == 'xncc':
            break

    if xncc['name'] != 'xncc':
        print("Error! xncc section was not found!", file=sys.stderr)
        return {}

    for cc in xncc['sections']:
        if cc['name'] == 'cc':
            break

    if cc['name'] != 'cc':
        print("Error! cc subsection of xncc was not found!", file=sys.stderr)
        return

    data = {
        'calclevel': cc['data']['CC level'],
        'cc_energy': cc['data']['energy']['total']['au'],
    }

    return data


def collect_eom_roots_xncc(cfour):
    """ Extracts EOM roots data from parsed CFOUR's output.
    returns:
        roots: list()
    """
    roots = []

    for xncc in cfour:
        if xncc['name'] != 'xncc':
            continue
        for eom in xncc['sections']:
            if eom['name'] != 'eom':
                continue
            for eom_irrep in eom['sections']:
                if eom_irrep['name'] != 'irrep':
                    continue
                irrep_data = eom_irrep['data']
                for eom_root in eom_irrep['sections']:
                    if eom_root['name'] != 'eom root':
                        continue
                    eom_model = eom_root['data']['model']
                    for eom_root_subsec in eom_root['sections']:
                        if eom_root_subsec['name'] == 'converged root':
                            converged_root = eom_root_subsec['data']
                            continue

                        if eom_root_subsec['name'] == 'EOM energy':
                            root_energy = eom_root_subsec['data']
                            continue

                    roots += [{
                        'model': eom_model,
                        'irrep': dict(irrep_data),
                        'converged root': converged_root,
                        'energy': root_energy,
                    }]
        break

    if len(roots) == 0:
        print("Info: No xncc EOM roots found.",
              file=sys.stderr)

    return roots


def print_cfour_excite_section(roots):
    """
    Prints the collected EOM roots as an input to the CFOUR's %excite* section
    The roots are sorted by their total energy.
    """

    roots.sort(key=lambda x: x['energy']['total']['au'])
    n_roots = len(roots)
    print("%excite*")
    print(n_roots)
    for root in roots:
        singles = [single for single in root['converged root']['singles'] if
                   abs(single['amplitude']) > SINGLE_THRESHOLD]
        n_singles = len(singles)
        print(f"{n_singles}")
        for single in singles:
            print(f"1 {single['I']} 0 {single['A']} 0 "
                  f"{single['amplitude']:.3f}")


def print_eom_roots_summary(roots, print_lvl):
    """
    Presents a summary of collected eom roots that is helpful for the
    writing the excite section of another CFOUR's input.
    """
    roots.sort(key=lambda x: x['energy']['total']['au'])
    n_roots = len(roots)
    for root in roots:
        irrep_no = root['irrep']['#']
        irrep_energy_no = root['irrep']['energy #']
        irrep_name = root['irrep']['name']
        id = root['ids']['#']
        energy_id = root['ids']['energy #']
        print(f"{id:2}: Root {energy_id+1:2d}/{n_roots}: "
              f"{irrep_energy_no} {irrep_name:3} (irrep #{irrep_no}): "
              f"{root['energy']['excitation']['eV']:6.3f} eV")

        # Print singles only with double flag
        if print_lvl < 2:
            continue

        print("Singles:")
        singles = [single for single in root['converged root']['singles'] if
                   abs(single['amplitude']) > SINGLE_THRESHOLD]
        n_singles = len(singles)
        print(f"{n_singles}")
        for single in singles:
            print(f"1 {single['I']} 0 {single['A']} 0 "
                  f"{single['amplitude']:.3f}")

        # Print doubles only with triple flag
        if print_lvl < 3:
            continue
        print("Doubles:")
        doubles = [double for double in root['converged root']['doubles'] if
                   abs(double['amplitude']) > DOUBLE_THRESHOLD]
        n_doubles = len(doubles)
        print(f"{n_doubles}")
        for double in doubles:
            print(f"{double['I']} {double['J']} {double['A']} {double['B']} "
                  f"{double['amplitude']:.3f}")

        print("\n")


def print_eom_roots_for_CBS_fitting(roots, cfour):
    """
    Presents a summary of collected eom roots that is helpful for the
    complte basis set extrapolation.
    """

    basis = get_basis(cfour)
    scf = get_scf_energy(cfour)
    cbs_input = {
        'basis': basis,
        'scf': scf,
    }
    cc = get_cc_data(cfour)
    cbs_input.update(cc)
    cbs_input['EOM'] = list()
    for root in roots:
        cbs_input['EOM'] += [{
            'irrep': {
                'name': root['irrep']['name'],
                'energy #': root['irrep']['energy #'],
            },
            'energy': root['energy']['total']['au'],
            'model': root['model'],
        }]

    print(json.dumps(cbs_input))

    return cbs_input


def add_root_ids(roots: list) -> None:
    """
    For each root in the list add an ordering number '#' that does not
    correspond to anything but it a unique number assigend to each root.

    For each root assign also the 'energy #', which tells the state number
    when states are sorted in by their total energy.

    The ids are saved as a dictionary under the key 'ids' of the root.
    """
    for counter, root in enumerate(roots):
        root['ids'] = {'#': counter}

    roots.sort(key=lambda x: x['energy']['total']['au'])
    for counter, root in enumerate(roots):
        root['ids']['energy #'] = counter


def main():
    args = get_args()
    with open(args.cfour_file, 'r') as cfour_file_input:
        cfour = json.load(cfour_file_input)

    roots = collect_eom_roots_xncc(cfour)
    add_root_ids(roots)
    add_irrep_energy_no_and_name(roots, cfour)

    if args.cbs is True:
        print_eom_roots_for_CBS_fitting(roots, cfour)

    if args.excite is True:
        print_cfour_excite_section(roots)

    if args.json is True:
        print(json.dumps(roots))

    if args.summary > 0:
        print_eom_roots_summary(roots, args.summary)


if __name__ == "__main__":
    main()
