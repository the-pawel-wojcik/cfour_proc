# CFOUR's processors
Scripts that work with parsed CFOUR output files. The 
[cfour parser](https://github.com/the-pawel-wojcik/cfour_parser).

# Examples
## Show EOM energies summary
```bash
cfour_parser -j output.c4 | jq > output.json
print_roots.py -s output.json 
```

## Show geometry optimization
The geometry.xyz file will contain all geometries, click through them to see
changes.
```bash
cfour_parser -j output.c4 | jq > output.json
geometry.py -v output.json > geometry.xyz
jmol geometry.xyz
```

## Show normal modes
```bash
cfour_parser -j output.c4 | jq > output.json
print_normal_coordinates.py -xyz output.json > nmodes.xyz
```
The `nmodes.xyz` file can be viewed with jmol.
