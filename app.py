import streamlit as st


import streamlit as st

from qe_generator import generate_qe_input

def count_non_empty_lines(text):
    """
    Count non-empty lines in a multiline text box.
    """
    return len([line for line in text.splitlines() if line.strip()])


def validate_atomic_species(atomic_species_text, expected_ntyp):
    """
    Validate ATOMIC_SPECIES section.
    Each valid line should have:
    Element AtomicMass PseudopotentialFile

    Example:
    Ba 137.327 Ba.upf
    """
    errors = []
    warnings = []

    lines = [line.strip() for line in atomic_species_text.splitlines() if line.strip()]

    if len(lines) != expected_ntyp:
        errors.append(
            f"ntyp is {expected_ntyp}, but ATOMIC_SPECIES contains {len(lines)} non-empty line(s)."
        )

    for i, line in enumerate(lines, start=1):
        parts = line.split()

        if len(parts) != 3:
            errors.append(
                f"ATOMIC_SPECIES line {i} should contain 3 values: Element AtomicMass PseudopotentialFile."
            )
            continue

        element, mass, pseudo_file = parts

        try:
            float(mass)
        except ValueError:
            errors.append(
                f"ATOMIC_SPECIES line {i}: atomic mass '{mass}' is not a valid number."
            )

        if not pseudo_file.endswith((".upf", ".UPF")):
            warnings.append(
                f"ATOMIC_SPECIES line {i}: pseudopotential file '{pseudo_file}' does not end with .upf."
            )

    return errors, warnings


def validate_cell_parameters(cell_parameters_text):
    """
    Validate CELL_PARAMETERS section.
    It should contain exactly 3 non-empty rows.
    Each row should contain 3 numbers.
    """
    errors = []

    lines = [line.strip() for line in cell_parameters_text.splitlines() if line.strip()]

    if len(lines) != 3:
        errors.append(
            f"CELL_PARAMETERS should contain exactly 3 non-empty rows, but it contains {len(lines)}."
        )

    for i, line in enumerate(lines, start=1):
        parts = line.split()

        if len(parts) != 3:
            errors.append(
                f"CELL_PARAMETERS line {i} should contain exactly 3 numbers."
            )
            continue

        for value in parts:
            try:
                float(value)
            except ValueError:
                errors.append(
                    f"CELL_PARAMETERS line {i}: '{value}' is not a valid number."
                )

    return errors


def validate_atomic_positions(atomic_positions_text, expected_nat):
    """
    Validate ATOMIC_POSITIONS section.
    Each valid line should have:
    Element x y z

    Example:
    Ba 2.0038408200 2.0038408200 2.0038408200
    """
    errors = []

    lines = [line.strip() for line in atomic_positions_text.splitlines() if line.strip()]

    if len(lines) != expected_nat:
        errors.append(
            f"nat is {expected_nat}, but ATOMIC_POSITIONS contains {len(lines)} non-empty line(s)."
        )

    for i, line in enumerate(lines, start=1):
        parts = line.split()

        if len(parts) != 4:
            errors.append(
                f"ATOMIC_POSITIONS line {i} should contain 4 values: Element x y z."
            )
            continue

        element = parts[0]
        coordinates = parts[1:]

        for value in coordinates:
            try:
                float(value)
            except ValueError:
                errors.append(
                    f"ATOMIC_POSITIONS line {i}: coordinate '{value}' is not a valid number."
                )

    return errors


def validate_k_points(k_points_type, k_points_text):
    """
    Validate K_POINTS section.

    For automatic:
    Expected format: kx ky kz sx sy sz
    Example: 4 4 4 0 0 0

    For gamma:
    Usually no extra values are needed.

    For crystal/tpiba:
    We allow multiline values, but do basic non-empty checking.
    """
    errors = []
    warnings = []

    text = k_points_text.strip()

    if k_points_type == "automatic":
        parts = text.split()

        if len(parts) != 6:
            errors.append(
                "K_POINTS automatic should contain exactly 6 values: kx ky kz sx sy sz."
            )
        else:
            for value in parts:
                try:
                    int(value)
                except ValueError:
                    errors.append(
                        f"K_POINTS automatic value '{value}' should be an integer."
                    )

    elif k_points_type == "gamma":
        if text:
            warnings.append(
                "K_POINTS gamma usually does not need extra values. You can leave the K_POINTS box empty."
            )

    elif k_points_type in ["crystal", "tpiba"]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if len(lines) == 0:
            errors.append(
                f"K_POINTS {k_points_type} requires multiline k-point data."
            )
        else:
            try:
                number_of_kpoints = int(lines[0].split()[0])
                actual_kpoint_lines = len(lines) - 1

                if actual_kpoint_lines != number_of_kpoints:
                    errors.append(
                        f"K_POINTS {k_points_type}: first line says {number_of_kpoints} k-points, but {actual_kpoint_lines} k-point line(s) were entered."
                    )
            except ValueError:
                errors.append(
                    f"K_POINTS {k_points_type}: first line should start with the number of k-points."
                )

    return errors, warnings

st.set_page_config(
    page_title="Quantum ESPRESSO Input Generator",
    page_icon="⚛️",
    layout="wide",
)


st.title("Quantum ESPRESSO pw.x Input Generator")

st.write(
    """
    This GUI helps you generate a Quantum ESPRESSO `pw.x` input file.
    Fill in the values below and download the generated `espresso.pwi` file.
    """
)


# -----------------------------
# CONTROL SECTION
# -----------------------------

st.header("1. CONTROL section")

col1, col2, col3 = st.columns(3)

with col1:
    calculation = st.selectbox(
        "calculation",
        ["scf", "relax", "vc-relax", "nscf", "bands"],
        index=0,
        help="Type of calculation to perform.",
    )

    verbosity = st.selectbox(
        "verbosity",
        ["high", "low"],
        index=0,
        help="Amount of output printed by Quantum ESPRESSO.",
    )

with col2:
    restart_mode = st.selectbox(
        "restart_mode",
        ["from_scratch", "restart"],
        index=0,
        help="Use from_scratch for a new calculation.",
    )

    pseudo_dir = st.text_input(
        "pseudo_dir",
        value="./",
        help="Folder where pseudopotential files are located.",
    )

with col3:
    tstress = st.checkbox(
        "tstress",
        value=True,
        help="Calculate and print stress.",
    )

    tprnfor = st.checkbox(
        "tprnfor",
        value=True,
        help="Calculate and print forces.",
    )


# -----------------------------
# SYSTEM SECTION
# -----------------------------

st.header("2. SYSTEM section")

col1, col2, col3 = st.columns(3)

with col1:
    ecutwfc = st.number_input(
        "ecutwfc",
        min_value=0.0,
        value=30.0,
        step=5.0,
        help="Plane-wave kinetic energy cutoff.",
    )

    ecutrho = st.number_input(
        "ecutrho",
        min_value=0.0,
        value=240.0,
        step=10.0,
        help="Charge density cutoff.",
    )

    ibrav = st.number_input(
        "ibrav",
        value=0,
        step=1,
        help="Bravais lattice index. Use 0 when CELL_PARAMETERS are given manually.",
    )

with col2:
    occupations = st.selectbox(
        "occupations",
        ["smearing", "fixed"],
        index=0,
        help="Use smearing for metals or small-gap systems; fixed for insulators.",
    )

    smearing = st.selectbox(
        "smearing",
        ["mp", "gaussian", "mv", "fd"],
        index=0,
        help="Smearing type.",
    )

    degauss = st.number_input(
        "degauss",
        min_value=0.0,
        value=0.001,
        step=0.001,
        format="%.6f",
        help="Smearing width.",
    )

with col3:
    nspin = st.number_input(
        "nspin",
        min_value=1,
        value=1,
        step=1,
        help="Spin polarization. Use 1 for non-spin-polarized calculations.",
    )

    ntyp = st.number_input(
        "ntyp",
        min_value=1,
        value=3,
        step=1,
        help="Number of atomic species.",
    )

    nat = st.number_input(
        "nat",
        min_value=1,
        value=5,
        step=1,
        help="Number of atoms in the unit cell.",
    )


# -----------------------------
# ELECTRONS SECTION
# -----------------------------

st.header("3. ELECTRONS section")

col1, col2, col3 = st.columns(3)

with col1:
    mixing_mode = st.selectbox(
        "mixing_mode",
        ["plain", "TF", "local-TF"],
        index=0,
        help="Charge mixing mode.",
    )

with col2:
    mixing_beta = st.number_input(
        "mixing_beta",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Mixing factor for self-consistency.",
    )

with col3:
    diagonalization = st.selectbox(
        "diagonalization",
        ["david", "cg", "paro"],
        index=0,
        help="Diagonalization method.",
    )


# -----------------------------
# ATOMIC SPECIES
# -----------------------------

st.header("4. ATOMIC_SPECIES section")

atomic_species = st.text_area(
    "Enter atomic species",
    value="""Ba 137.327 Ba.upf
Ti 47.867 Ti.upf
O 15.999 O.upf""",
    height=120,
    help="Format: Element AtomicMass PseudopotentialFile",
)

st.caption(
    "Example format: `Ba 137.327 Ba.upf`"
)


# -----------------------------
# CELL PARAMETERS
# -----------------------------

st.header("5. CELL_PARAMETERS section")

cell_parameters = st.text_area(
    "Enter cell parameters in angstrom",
    value="""4.00768164000000 0.00000000000000 0.00000000000000
0.00000000000000 4.00768164000000 0.00000000000000
0.00000000000000 0.00000000000000 4.00768164000000""",
    height=130,
    help="Three lattice vectors. Each row should contain x y z values.",
)

st.caption(
    "Use three rows. Each row represents one lattice vector."
)


# -----------------------------
# ATOMIC POSITIONS
# -----------------------------

st.header("6. ATOMIC_POSITIONS section")

atomic_positions = st.text_area(
    "Enter atomic positions in angstrom",
    value="""Ba 2.0038408200 2.0038408200 2.0038408200
Ti 0.0000000000 0.0000000000 0.0000000000
O 2.0038408200 0.0000000000 0.0000000000
O 0.0000000000 2.0038408200 0.0000000000
O 0.0000000000 0.0000000000 2.0038408200""",
    height=170,
    help="Format: Element x y z",
)

st.caption(
    "Example format: `Ba 2.0038408200 2.0038408200 2.0038408200`"
)


# -----------------------------
# K POINTS
# -----------------------------

# -----------------------------
# K POINTS
# -----------------------------

st.header("7. K_POINTS section")

k_points_type = st.selectbox(
    "K_POINTS type",
    ["automatic", "gamma", "crystal", "tpiba"],
    index=0,
    help="Choose the K_POINTS format.",
)

k_points = st.text_area(
    "Enter K_POINTS values",
    value="4 4 4 0 0 0",
    height=100,
    help=(
        "For automatic: kx ky kz sx sy sz\n"
        "For gamma: leave this box empty\n"
        "For crystal/tpiba: enter number of points and coordinates."
    ),
)

# -----------------------------
# GENERATE INPUT FILE
# -----------------------------

qe_input = generate_qe_input(
    calculation=calculation,
    verbosity=verbosity,
    restart_mode=restart_mode,
    pseudo_dir=pseudo_dir,
    tstress=tstress,
    tprnfor=tprnfor,
    ecutwfc=ecutwfc,
    ecutrho=ecutrho,
    occupations=occupations,
    degauss=degauss,
    smearing=smearing,
    nspin=nspin,
    ntyp=ntyp,
    nat=nat,
    ibrav=ibrav,
    mixing_mode=mixing_mode,
    mixing_beta=mixing_beta,
    diagonalization=diagonalization,
    atomic_species=atomic_species,
    cell_parameters=cell_parameters,
    atomic_positions=atomic_positions,
    k_points_type=k_points_type,
    k_points=k_points,
)


# -----------------------------
# VALIDATION
# -----------------------------

validation_errors = []
validation_warnings = []

species_errors, species_warnings = validate_atomic_species(
    atomic_species_text=atomic_species,
    expected_ntyp=ntyp,
)

cell_errors = validate_cell_parameters(
    cell_parameters_text=cell_parameters,
)

position_errors = validate_atomic_positions(
    atomic_positions_text=atomic_positions,
    expected_nat=nat,
)

kpoint_errors, kpoint_warnings = validate_k_points(
    k_points_type=k_points_type,
    k_points_text=k_points,
)

validation_errors.extend(species_errors)
validation_errors.extend(cell_errors)
validation_errors.extend(position_errors)
validation_errors.extend(kpoint_errors)

validation_warnings.extend(species_warnings)
validation_warnings.extend(kpoint_warnings)


# -----------------------------
# SHOW VALIDATION AND PREVIEW
# -----------------------------

st.header("8. Validation and generated Quantum ESPRESSO input file")

st.markdown(
    """
    Official Quantum ESPRESSO `pw.x` input documentation:  
    [https://www.quantum-espresso.org/Doc/INPUT_PW.html](https://www.quantum-espresso.org/Doc/INPUT_PW.html)
    """
)

if validation_errors:
    st.error("Please fix the following error(s) before using the input file:")

    for error in validation_errors:
        st.write(f"❌ {error}")
else:
    st.success("No critical errors detected.")

if validation_warnings:
    st.warning("Please review the following warning(s):")

    for warning in validation_warnings:
        st.write(f"⚠️ {warning}")

st.subheader("Generated input preview")

st.code(qe_input, language="text")

# -----------------------------
# DOWNLOAD FILE
# -----------------------------

st.header("9. Download file")

output_file_name = st.text_input(
    "Output file name, e.g. espresso.pwi",
    value="espresso.pwi",
    help="You can use any extension, for example .pwi, .in, .txt, or .py.",
)

if output_file_name.strip() == "":
    output_file_name = "espresso.pwi"
else:
    output_file_name = output_file_name.strip()

download_disabled = len(validation_errors) > 0

if download_disabled:
    st.info("Fix the validation errors above before downloading the file.")

st.download_button(
    label=f"Download {output_file_name}",
    data=qe_input,
    file_name=output_file_name,
    mime="text/plain",
    key="download_qe_input_file",
    disabled=download_disabled,
)