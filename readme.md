# CFOUR's processors
Scripts that work with parsed CFOUR output files. 

# Examples
## Show EOM energies summary
```
cfour_parser -j output.c4 | jq > output.json
print_roots.py -s output.json 
```

## Show geometry optimization
The geometry.xyz file will contain all geometries, click through them to see
changes.
```
xcfour.py -j output.c4 | jq > output.json
geometry.py -v output.json > geometry.xyz
jmol geometry.xyz
```
