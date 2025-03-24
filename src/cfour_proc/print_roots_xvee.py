#!/usr/bin/env python3

import argparse
import json
import sys
from irrep_no_to_name import get_irrep_no_to_name

au2eV = 27.211386245988

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


def add_irrep_energy_no_and_name(roots, cfour):
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


def add_excitation_energy(roots, cc_energy_au: float):
    for root in roots:
        excitation_energy_au = root['energy']['total']['au'] - cc_energy_au
        root['energy']['excitation'] = {
            'au': excitation_energy_au,
            'eV': excitation_energy_au * au2eV,
        }


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
        return

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


def collect_eom_roots_xvee(cfour):
    """ Extracts EOM roots data from parsed CFOUR's output.
    returns:
        roots: list()
    """
    roots = []

    for xvee in cfour:
        if xvee['name'] != 'xvee':
            continue
        for solution in xvee['sections']:
            if solution['name'] != 'eom solution':
                continue

            # TODO: move the metadata test to a separate module
            if solution['metadata']['ok'] is False:
                if 'start' in solution:
                    start = solution['start']
                else:
                    start = 0

                if 'end' in solution:
                    end = solution['end']
                else:
                    end = -1

                print("Warning: Cannot read from an ivalid section "
                      f"{solution['name']} (lines {start}-{end}).",
                      file=sys.stderr)
                continue

            eom_model = solution['data']['model']
            root_energy = solution['data']['energy']
            irrep = solution['data']['irrep']

            roots += [{
                'model': eom_model,
                'irrep': irrep,
                'energy': root_energy,
            }]

        break

    if len(roots) == 0:
        print("Info: No xvee EOM roots found.", file=sys.stderr)

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
              f"{root['energy']['excitation']['eV']:6.3f} eV"
              f" ({root['energy']['total']['au']:6.3f} Ha).")

        # Print singles only with double flag
        if print_lvl < 2:
            continue

        # TODO: not available for xvee
        print("TODO: only basic printout is available so far for xvee.")
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
    # TODO: get_cc_data works only with xncc
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


# TODO: this function is shared with print_roots for xncc make is a library.
def add_root_ids(roots):
    """
    For each root in the list add an ordering number '#' that does not
    correspond to anything but it a unique number assigned to each root.

    For each root assigned also the 'energy #', which tells which orders the
    states by their energy.

    The ids are saved as a dictionary under the key 'ids' of the root.

    Input:
        roots: list()
    """
    for counter, root in enumerate(roots):
        root['ids'] = {'#': counter}

    roots.sort(key=lambda x: x['energy']['total']['au'])
    for counter, root in enumerate(roots):
        root['ids']['energy #'] = counter


def collect_ccsd(cfour) -> list[float]:
    """ Extract total CC energy from every xvcc program run.
    returns:
        roots: list[float]
    """
    cc_total_energies_au = []

    for xvcc in cfour:
        if xvcc['name'] != 'xvcc':
            continue
        for miracle in xvcc['sections']:
            if miracle['name'] != 'A miracle':
                continue

            # TODO: move the metadata test to a separate module
            if miracle['metadata']['ok'] is False:
                if 'start' in miracle:
                    start = miracle['start']
                else:
                    start = 0

                if 'end' in miracle:
                    end = miracle['end']
                else:
                    end = -1

                print("Warning: Cannot read from an ivalid section "
                      f"{miracle['name']} (lines {start}-{end}).",
                      file=sys.stderr)
                continue

            cc_total_energy_au = miracle['data']['energy']['total']['au']
            cc_total_energies_au += [cc_total_energy_au]

    if len(cc_total_energies_au) == 0:
        print("Info: No CC total energies found in xvcc.", file=sys.stderr)

    return cc_total_energies_au


def main():
    args = get_args()
    with open(args.cfour_file, 'r') as cfour_file_input:
        cfour = json.load(cfour_file_input)

    cc_energies = collect_ccsd(cfour)
    roots = collect_eom_roots_xvee(cfour)
    add_root_ids(roots)
    add_irrep_energy_no_and_name(roots, cfour)
    add_excitation_energy(roots, cc_energies[0])

    # TODO: implement xvcc parsing from xvcc
    # TODO: xvcc is ready!
    if args.cbs is True:
        print("TODO: implement cc parsing for xvcc", file=sys.stderr)
        # print_eom_roots_for_CBS_fitting(roots, cfour)

    # TODO: implement parsing of converged root section of xvee
    if args.excite is True:
        print("TODO: implement parsing of converged root section of xvee",
              file=sys.stderr)
        # print_cfour_excite_section(roots)

    if args.json is True:
        print(json.dumps(roots))

    if args.summary > 0:
        print_eom_roots_summary(roots, args.summary)


if __name__ == "__main__":
    main()
