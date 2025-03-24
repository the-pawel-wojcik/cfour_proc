import argparse
import shutil
import os
from pathlib import Path

# TODO: do not overwrite existing files, unless requested to do so.

def log(msg: str):
    with open('log.opt2vib.md', 'a', encoding='utf-8') as readme:
        readme.write(msg + '\n')


parser = argparse.ArgumentParser()
parser.add_argument('ZMATnew')
args = parser.parse_args()


log(f"""Optimized geometry file comes from:
    `{os.path.abspath(args.ZMATnew)}`""")


shutil.copy2(src=args.ZMATnew, dst='.')
cwd = Path('.')
(cwd / 'ZMATnew').rename(target=(cwd / 'ZMAT.tmp'))
log("ZMATnew renamed to ZMAT.tmp")


old_zmat = dict()
with open('ZMAT.tmp', 'r', encoding='utf-8') as zmattmp:
    old_zmat['comment'] = next(zmattmp)
    old_zmat['geometry'] = list()
    for line in zmattmp:
        if line.strip() == '':
            break
        old_zmat['geometry'].append(line.replace('*', ''))

    old_zmat['reminder'] = list()
    for line in zmattmp:
        old_zmat['reminder'].append(line)

log('Removed `*` symbols from the geometry specification (Z-matrix).')

# TODO: parse the CFOUR*() section
# TODO: remove the optimization keywords: geo_conv, lineq_conv
# TODO: consider consider setting the convergence options: (scf|cc|estate)_covn
# TODO: based on the type of calculation specify which vib method to use
# TODO: add the vib keywords: vib, freq_algo, lineq_conv
# TODO: consider specifying the FINDIFF keywords: FD_CALCTYPE, FD_STEPSIZE,
#       FD_PROJECT, and FD_IRREPS

with open('ZMAT', 'w', encoding='utf-8') as zmat_file:
    zmat_file.write(old_zmat['comment'])
    for line in old_zmat['geometry']:
        zmat_file.write(line)
    zmat_file.write('\n')
    for line in old_zmat['reminder']:
        zmat_file.write(line)
log('Edited file saved to ZMAT.')

(cwd / 'ZMAT.tmp').unlink()
log('Removed the "ZMAT.tmp" file.')

(cwd / 'findiff').mkdir()
log('Created a "findiff" directory.')

(cwd / 'ZMAT').rename(target=(cwd / 'findiff' / 'ZMAT'))
log('Moved the "ZMAT" file to the "findiff" directory.')
