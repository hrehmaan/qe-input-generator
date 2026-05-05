# Quantum ESPRESSO Input PWI Generator

A beginner-friendly browser-based GUI for generating, validating, editing, downloading, and testing small Quantum ESPRESSO `pw.x` input files.

The app helps users prepare Quantum ESPRESSO input files without writing the full script manually.

For Docker-based Quantum ESPRESSO installation and usage, see:

[QE Docker Setup](https://github.com/hrehmaan/qe-docker)

---

## Use the app online

Click here to use the GUI directly in your browser:

👉 [Open QE Input PWI Generator](https://qe-input-pwi-generator.streamlit.app/)

Direct link:

```text
https://qe-input-pwi-generator.streamlit.app/
```

No installation is required.  
No coding is required.  
No repository download is required.

---

## Main features

- Browser-based Streamlit GUI
- Generates Quantum ESPRESSO `pw.x` input files
- Supports editable final preview before download
- Supports common `pw.x` namelists and cards
- Materials Project structure fetching by material ID
- Primitive and conventional standard cell generation using pymatgen
- Automatic `CELL_PARAMETERS` and `ATOMIC_POSITIONS` generation
- Automatic `nat`, `ntyp`, and element detection from fetched structures
- Optional advanced settings through checkboxes
- Structural validation before download
- Validation checklist
- ATOMIC_SPECIES helper with built-in atomic masses
- Suggested & Custom pseudopotential filenames
- Temporary pseudopotential upload for online smoke checks
- Online tiny Quantum ESPRESSO smoke check for small inputs

---

## Materials Project structure helper

The app includes an optional Materials Project structure helper.

Users can enter their own Materials Project API key and a material ID, such as:

```text
mp-34202

## Supported input sections

The app currently supports common `pw.x` sections including:

```text
&CONTROL
&SYSTEM
&ELECTRONS
&IONS
&CELL
ATOMIC_SPECIES
CELL_PARAMETERS
ATOMIC_POSITIONS
K_POINTS
```

The generated input follows the standard Quantum ESPRESSO `pw.x` input order.

---

## Online QE smoke check

The app can run a small online Quantum ESPRESSO smoke check using a backend service.

This check can confirm that:

- the generated input is sent correctly
- required pseudopotential files were uploaded
- `pw.x` can start reading or running the input
- simple small calculations can run successfully

The online smoke check is intended for small test cases only.

Current safety limits:

```text
Maximum atoms for online QE smoke check: nat <= 30
Maximum uploaded pseudopotential files: 10
Maximum pseudopotential file size: 20 MB each
Temporary files auto-delete after: 10 minutes
```

For larger systems, users should download the generated input file and run it locally, in Docker, or on an HPC cluster.

---

## Pseudopotential handling

The app does not store a full pseudopotential library.

Instead, it provides:

- built-in atomic masses
- suggested pseudopotential filenames
- custom filename entry
- upload option for required `.UPF` files during online smoke checks

Uploaded pseudopotential files are stored temporarily by the backend and deleted automatically after 10 minutes.

Users should make sure that selected pseudopotentials are appropriate for their calculations.

Useful pseudopotential resources:

- [Quantum ESPRESSO pseudopotentials](https://www.quantum-espresso.org/pseudopotentials/)
- [Quantum ESPRESSO legacy pseudopotential tables](https://pseudopotentials.quantum-espresso.org/legacy_tables)

---

## Validation scope

The validation is based on common Quantum ESPRESSO `pw.x` input syntax from the official `INPUT_PW` documentation.

The app checks common structural and formatting rules such as:

- `nat` matches the number of `ATOMIC_POSITIONS` lines
- `ntyp` matches the number of `ATOMIC_SPECIES` lines
- atomic symbols in `ATOMIC_POSITIONS` exist in `ATOMIC_SPECIES`
- `CELL_PARAMETERS` is required when `ibrav = 0`
- `CELL_PARAMETERS` is not used when `ibrav != 0`
- `K_POINTS automatic` has six integer values
- `K_POINTS gamma` does not require extra values
- selected pseudopotential filenames match uploaded files
- basic consistency of selected GUI options

The validation checks common formatting and consistency mistakes, but it does not implement every possible Quantum ESPRESSO input rule.

---

## Example generated input

```text
&CONTROL
    calculation = 'scf'
    pseudo_dir = './'
    prefix = 'qe'
    outdir = './tmp/'
/

&SYSTEM
    ibrav = 0
    nat = 5
    ntyp = 3
    ecutwfc = 60.0
    ecutrho = 480.0
/

&ELECTRONS
    conv_thr = 1e-06
    mixing_beta = 0.7
/

ATOMIC_SPECIES
Ba 137.327000 Ba.upf
Ti 47.867000 Ti.upf
O 15.999000 O.upf

CELL_PARAMETERS angstrom
4.000000 0.000000 0.000000
0.000000 4.000000 0.000000
0.000000 0.000000 4.000000

ATOMIC_POSITIONS crystal
Ba 0.000000 0.000000 0.000000
Ti 0.500000 0.500000 0.500000
O  0.500000 0.500000 0.000000
O  0.500000 0.000000 0.500000
O  0.000000 0.500000 0.500000

K_POINTS automatic
4 4 4 0 0 0
```

---

## Run locally

Clone the repository:

```bash
git clone https://github.com/hrehmaan/qe-input-generator.git
cd qe-input-generator
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run app.py
```

---

## Run the backend locally with Docker

The backend is used for temporary pseudopotential upload and the online QE smoke check.

Go to the backend folder:

```bash
cd qe-runner-backend
```

Build the Docker image:

```bash
docker build -t qe-runner-backend .
```

Run the backend:

```bash
docker run --rm -p 8000:8000 qe-runner-backend
```

Then open:

```text
http://127.0.0.1:8000
```

Expected response:

```json
{
  "status": "ok",
  "message": "QE Runner Backend is running."
}
```

For local Streamlit testing, the app uses:

```text
http://127.0.0.1:8000
```

For the deployed app, the backend URL is configured using Streamlit secrets.

---

## Docker-based Quantum ESPRESSO setup

To install and run Quantum ESPRESSO using Docker, see:

[QE Docker Setup](https://github.com/hrehmaan/qe-docker)

---

## Official references

- [Quantum ESPRESSO official website](https://www.quantum-espresso.org/)
- [INPUT_PW documentation](https://www.quantum-espresso.org/Doc/INPUT_PW.html)
- [Quantum ESPRESSO source repository](https://gitlab.com/QEF/q-e)
- [Quantum ESPRESSO pseudopotentials](https://www.quantum-espresso.org/pseudopotentials/)
- [Legacy pseudopotential tables](https://pseudopotentials.quantum-espresso.org/legacy_tables)
- [Materials Project](https://next-gen.materialsproject.org/)
- [pymatgen Python library](https://pymatgen.org/)

---


## Contributing

Contributions are very welcome, but please read the contributing guide first:

[Contributing guidelines](CONTRIBUTING.md)

Before making a large change, please open a GitHub issue:

[GitHub issues](https://github.com/hrehmaan/qe-input-generator/issues)

---

## License

MIT