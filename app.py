
import streamlit as st

from qe_generator import generate_qe_input
import streamlit.components.v1 as components

ATOMIC_MASSES = {
    "H": 1.008,
    "He": 4.002602,
    "Li": 6.94,
    "Be": 9.0121831,
    "B": 10.81,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.998403163,
    "Ne": 20.1797,
    "Na": 22.98976928,
    "Mg": 24.305,
    "Al": 26.9815385,
    "Si": 28.085,
    "P": 30.973761998,
    "S": 32.06,
    "Cl": 35.45,
    "Ar": 39.948,
    "K": 39.0983,
    "Ca": 40.078,
    "Sc": 44.955908,
    "Ti": 47.867,
    "V": 50.9415,
    "Cr": 51.9961,
    "Mn": 54.938044,
    "Fe": 55.845,
    "Co": 58.933194,
    "Ni": 58.6934,
    "Cu": 63.546,
    "Zn": 65.38,
    "Ga": 69.723,
    "Ge": 72.630,
    "As": 74.921595,
    "Se": 78.971,
    "Br": 79.904,
    "Kr": 83.798,
    "Rb": 85.4678,
    "Sr": 87.62,
    "Y": 88.90584,
    "Zr": 91.224,
    "Nb": 92.90637,
    "Mo": 95.95,
    "Tc": 98.0,
    "Ru": 101.07,
    "Rh": 102.90550,
    "Pd": 106.42,
    "Ag": 107.8682,
    "Cd": 112.414,
    "In": 114.818,
    "Sn": 118.710,
    "Sb": 121.760,
    "Te": 127.60,
    "I": 126.90447,
    "Xe": 131.293,
    "Cs": 132.90545196,
    "Ba": 137.327,
    "La": 138.90547,
    "Ce": 140.116,
    "Pr": 140.90766,
    "Nd": 144.242,
    "Pm": 145.0,
    "Sm": 150.36,
    "Eu": 151.964,
    "Gd": 157.25,
    "Tb": 158.92535,
    "Dy": 162.500,
    "Ho": 164.93033,
    "Er": 167.259,
    "Tm": 168.93422,
    "Yb": 173.045,
    "Lu": 174.9668,
    "Hf": 178.49,
    "Ta": 180.94788,
    "W": 183.84,
    "Re": 186.207,
    "Os": 190.23,
    "Ir": 192.217,
    "Pt": 195.084,
    "Au": 196.966569,
    "Hg": 200.592,
    "Tl": 204.38,
    "Pb": 207.2,
    "Bi": 208.98040,
}


PSEUDO_SUGGESTIONS = {
    "Ba": ["Ba.upf", "Ba.pbe-spn-kjpaw_psl.1.0.0.UPF"],
    "Ti": ["Ti.upf", "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF"],
    "O": ["O.upf", "O.pbe-n-kjpaw_psl.1.0.0.UPF"],
    "Bi": ["Bi_pbe_v1.uspp.F.UPF", "Bi.pbe-dn-kjpaw_psl.1.0.0.UPF"],
    "Te": ["Te_pbe_v1.uspp.F.UPF", "Te.pbe-n-kjpaw_psl.1.0.0.UPF"],
}


def normalize_element_symbol(symbol):
    """
    Normalize element symbols such as 'ba' -> 'Ba'.
    """
    symbol = symbol.strip()

    if not symbol:
        return ""

    return symbol[0].upper() + symbol[1:].lower()


def parse_element_list(text):
    """
    Parse elements from comma/space/newline separated text.
    Example: 'Ba Ti O' -> ['Ba', 'Ti', 'O']
    """
    raw_items = text.replace(",", " ").split()
    elements = []

    for item in raw_items:
        symbol = normalize_element_symbol(item)

        if symbol and symbol not in elements:
            elements.append(symbol)

    return elements


def detect_elements_from_atomic_positions(atomic_positions_text):
    """
    Detect unique element symbols from ATOMIC_POSITIONS text.
    """
    elements = []

    for line in atomic_positions_text.splitlines():
        line = line.strip()

        if not line:
            continue

        symbol = normalize_element_symbol(line.split()[0])

        if symbol and symbol not in elements:
            elements.append(symbol)

    return elements


def build_atomic_species_text(selected_elements, selected_pseudos):
    """
    Build ATOMIC_SPECIES text from selected elements and pseudopotentials.
    """
    lines = []

    for element in selected_elements:
        mass = ATOMIC_MASSES.get(element)
        pseudo = selected_pseudos.get(element, f"{element}.upf")

        if mass is None:
            mass = 0.0

        lines.append(f"{element} {mass:.6f} {pseudo}")

    return "\n".join(lines)



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


def validate_cell_parameters(cell_parameters_text, ibrav, use_cell_parameters):
    """
    Validate CELL_PARAMETERS section.

    Official QE rule:
    - Required if ibrav == 0
    - Must be absent if ibrav != 0
    """
    errors = []
    warnings = []

    text = cell_parameters_text.strip()

    if ibrav == 0:
        if not text:
            errors.append(
                "CELL_PARAMETERS is required when ibrav = 0."
            )
            return errors, warnings

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if len(lines) != 3:
            errors.append(
                f"CELL_PARAMETERS should contain exactly 3 non-empty rows when ibrav = 0, but it contains {len(lines)}."
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

    else:
        if use_cell_parameters and text:
            errors.append(
                "CELL_PARAMETERS must be absent when ibrav is not 0. Use A/B/C or celldm values instead."
            )

    return errors, warnings

def validate_atomic_positions(atomic_positions_text, expected_nat, atomic_species_text):
    """
    Validate ATOMIC_POSITIONS section.

    Standard format:
    Element x y z

    Optional QE format with fixed/free coordinates:
    Element x y z if_pos1 if_pos2 if_pos3

    Example:
    Ba 2.0038408200 2.0038408200 2.0038408200
    O  0.0000000000 0.0000000000 2.0038408200 1 1 0
    """
    errors = []
    warnings = []

    position_lines = [
        line.strip()
        for line in atomic_positions_text.splitlines()
        if line.strip()
    ]

    species_lines = [
        line.strip()
        for line in atomic_species_text.splitlines()
        if line.strip()
    ]

    species_symbols = set()

    for line in species_lines:
        parts = line.split()
        if parts:
            species_symbols.add(parts[0])

    if len(position_lines) != expected_nat:
        errors.append(
            f"nat is {expected_nat}, but ATOMIC_POSITIONS contains {len(position_lines)} non-empty line(s)."
        )

    for i, line in enumerate(position_lines, start=1):
        parts = line.split()

        if len(parts) not in [4, 7]:
            errors.append(
                f"ATOMIC_POSITIONS line {i} should contain either 4 values: Element x y z, or 7 values: Element x y z if_pos1 if_pos2 if_pos3."
            )
            continue

        element = parts[0]
        coordinates = parts[1:4]

        if element not in species_symbols:
            errors.append(
                f"ATOMIC_POSITIONS line {i}: element '{element}' is not listed in ATOMIC_SPECIES."
            )

        for value in coordinates:
            try:
                float(value)
            except ValueError:
                errors.append(
                    f"ATOMIC_POSITIONS line {i}: coordinate '{value}' is not a valid number."
                )

        if len(parts) == 7:
            flags = parts[4:7]

            for flag in flags:
                if flag not in ["0", "1"]:
                    errors.append(
                        f"ATOMIC_POSITIONS line {i}: if_pos values should be only 0 or 1."
                    )
                    break

    return errors, warnings

def validate_k_points(k_points_type, k_points_text):
    """
    Validate K_POINTS section based on official QE pw.x syntax.
    """
    errors = []
    warnings = []

    valid_k_types = [
        "gamma",
        "automatic",
        "crystal",
        "tpiba",
        "crystal_b",
        "tpiba_b",
        "crystal_c",
        "tpiba_c",
    ]

    if k_points_type not in valid_k_types:
        errors.append(
            f"Invalid K_POINTS type '{k_points_type}'. "
            f"Valid options are: {', '.join(valid_k_types)}."
        )
        return errors, warnings

    text = k_points_text.strip()

    if k_points_type == "gamma":
        if text:
            warnings.append(
                "K_POINTS gamma does not need extra values. "
                "The generated file will use only: K_POINTS gamma."
            )
        return errors, warnings

    if k_points_type == "automatic":
        parts = text.split()

        if len(parts) != 6:
            errors.append(
                "K_POINTS automatic should contain exactly 6 integer values: "
                "nk1 nk2 nk3 sk1 sk2 sk3."
            )
            return errors, warnings

        values = []

        for value in parts:
            try:
                values.append(int(value))
            except ValueError:
                errors.append(f"K_POINTS automatic value '{value}' must be an integer.")

        if errors:
            return errors, warnings

        nk1, nk2, nk3, sk1, sk2, sk3 = values

        if nk1 <= 0 or nk2 <= 0 or nk3 <= 0:
            errors.append("K_POINTS automatic nk1, nk2, nk3 must be positive integers.")

        for name, shift in [("sk1", sk1), ("sk2", sk2), ("sk3", sk3)]:
            if shift not in [0, 1]:
                errors.append(f"K_POINTS automatic {name} must be 0 or 1.")

        return errors, warnings

    listed_k_types = [
        "crystal",
        "tpiba",
        "crystal_b",
        "tpiba_b",
        "crystal_c",
        "tpiba_c",
    ]

    if k_points_type in listed_k_types:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if not lines:
            errors.append(
                f"K_POINTS {k_points_type} requires the first line to be the number of k-points."
            )
            return errors, warnings

        try:
            nks = int(lines[0].split()[0])
        except ValueError:
            errors.append(
                f"K_POINTS {k_points_type}: first line must start with the number of k-points."
            )
            return errors, warnings

        if nks <= 0:
            errors.append(f"K_POINTS {k_points_type}: nks must be positive.")
            return errors, warnings

        kpoint_lines = lines[1:]

        if len(kpoint_lines) != nks:
            errors.append(
                f"K_POINTS {k_points_type}: first line says {nks} k-points, "
                f"but {len(kpoint_lines)} k-point line(s) were entered."
            )

        if k_points_type in ["crystal_c", "tpiba_c"] and nks != 3:
            errors.append(
                f"K_POINTS {k_points_type} is for contour plots and must have exactly 3 k-points."
            )

        for i, line in enumerate(kpoint_lines, start=1):
            parts = line.split()

            if len(parts) < 4:
                errors.append(
                    f"K_POINTS {k_points_type} line {i} must contain at least "
                    "4 values: kx ky kz weight."
                )
                continue

            for value in parts[:4]:
                if not is_number(value):
                    errors.append(
                        f"K_POINTS {k_points_type} line {i}: '{value}' is not numeric."
                    )

        if k_points_type in ["crystal_b", "tpiba_b"]:
            warnings.append(
                f"K_POINTS {k_points_type} is used for band-structure paths. "
                "Check that the path follows the QE band-path convention."
            )

        return errors, warnings

    return errors, warnings


def validate_control_parameters(control_params):
    """
    Validate CONTROL options currently exposed in the GUI.
    """
    errors = []
    warnings = []

    valid_calculations = ["scf", "nscf", "bands", "relax", "md", "vc-relax", "vc-md"]
    valid_verbosity = ["high", "low"]
    valid_restart_mode = ["from_scratch", "restart"]

    if has_param(control_params, "calculation"):
        if control_params["calculation"] not in valid_calculations:
            errors.append(
                f"Invalid calculation '{control_params['calculation']}'. "
                f"Valid options are: {', '.join(valid_calculations)}."
            )

    if has_param(control_params, "verbosity"):
        if control_params["verbosity"] not in valid_verbosity:
            errors.append("verbosity must be 'low' or 'high'.")

    if has_param(control_params, "restart_mode"):
        if control_params["restart_mode"] not in valid_restart_mode:
            errors.append("restart_mode must be 'from_scratch' or 'restart'.")

    if has_param(control_params, "max_seconds"):
        if float(control_params["max_seconds"]) <= 0:
            errors.append("max_seconds must be positive.")

    if has_param(control_params, "wf_collect"):
        warnings.append(
            "wf_collect is obsolete and no longer implemented in recent QE versions."
        )

    if has_param(control_params, "etot_conv_thr"):
        if float(control_params["etot_conv_thr"]) <= 0:
            errors.append("etot_conv_thr must be positive.")

    if has_param(control_params, "forc_conv_thr"):
        if float(control_params["forc_conv_thr"]) <= 0:
            errors.append("forc_conv_thr must be positive.")

    return errors, warnings


def validate_system_parameters(system_params, ibrav, use_cell_parameters):
    """
    Validate SYSTEM options currently exposed in the GUI.
    """
    errors = []
    warnings = []

    lattice_errors, lattice_warnings = validate_lattice_parameters(
        system_params=system_params,
        ibrav=ibrav,
        use_cell_parameters=use_cell_parameters,
    )

    errors.extend(lattice_errors)
    warnings.extend(lattice_warnings)

    required_positive = ["nat", "ntyp", "ecutwfc"]

    for key in required_positive:
        if not has_param(system_params, key):
            errors.append(f"{key} is required in &SYSTEM.")
        elif float(system_params[key]) <= 0:
            errors.append(f"{key} must be positive.")

    if has_param(system_params, "ecutrho"):
        if float(system_params["ecutrho"]) <= 0:
            errors.append("ecutrho must be positive.")

        if has_param(system_params, "ecutwfc"):
            if float(system_params["ecutrho"]) < 4 * float(system_params["ecutwfc"]):
                warnings.append(
                    "ecutrho is less than 4 × ecutwfc. QE default is 4 × ecutwfc, "
                    "and ultrasoft pseudopotentials often need 8–12 × ecutwfc."
                )

    if has_param(system_params, "nbnd") and int(system_params["nbnd"]) <= 0:
        errors.append("nbnd must be a positive integer.")

    if has_param(system_params, "nspin"):
        nspin = int(system_params["nspin"])

        if nspin not in [1, 2, 4]:
            errors.append("nspin must be 1, 2, or 4.")

        if nspin == 4:
            errors.append(
                "QE documentation says not to specify nspin=4 directly; "
                "use noncolin=.TRUE. instead. This GUI does not yet support noncolin."
            )

    if has_param(system_params, "occupations"):
        valid_occupations = [
            "fixed",
            "smearing",
            "tetrahedra",
            "tetrahedra_lin",
            "tetrahedra_opt",
            "from_input",
        ]

        occupations = system_params["occupations"]

        if occupations not in valid_occupations:
            errors.append(
                f"Invalid occupations value '{occupations}'. "
                f"Valid options are: {', '.join(valid_occupations)}."
            )

        if occupations == "smearing":
            if not has_param(system_params, "smearing"):
                errors.append("smearing must be specified when occupations = 'smearing'.")
            if not has_param(system_params, "degauss"):
                errors.append("degauss must be specified when occupations = 'smearing'.")
            elif float(system_params["degauss"]) < 0:
                errors.append("degauss must be non-negative.")

        if occupations == "fixed":
            if has_param(system_params, "smearing") or has_param(system_params, "degauss"):
                warnings.append(
                    "occupations = 'fixed' normally does not need smearing or degauss."
                )

    if has_param(system_params, "smearing"):
        valid_smearing = [
            "gaussian",
            "gauss",
            "methfessel-paxton",
            "m-p",
            "mp",
            "marzari-vanderbilt",
            "cold",
            "m-v",
            "mv",
            "fermi-dirac",
            "f-d",
            "fd",
        ]

        if system_params["smearing"] not in valid_smearing:
            errors.append(
                f"Invalid smearing value '{system_params['smearing']}'. "
                f"Valid options are: {', '.join(valid_smearing)}."
            )

    return errors, warnings


def validate_electrons_parameters(electrons_params):
    """
    Validate ELECTRONS options currently exposed in the GUI.
    """
    errors = []
    warnings = []

    if has_param(electrons_params, "conv_thr") and float(electrons_params["conv_thr"]) <= 0:
        errors.append("conv_thr must be positive.")

    if has_param(electrons_params, "electron_maxstep") and int(electrons_params["electron_maxstep"]) <= 0:
        errors.append("electron_maxstep must be a positive integer.")

    if has_param(electrons_params, "mixing_beta"):
        mixing_beta = float(electrons_params["mixing_beta"])
        if mixing_beta <= 0 or mixing_beta > 1:
            errors.append("mixing_beta should be greater than 0 and less than or equal to 1.")

    if has_param(electrons_params, "mixing_mode"):
        valid_mixing_mode = ["plain", "TF", "local-TF"]
        if electrons_params["mixing_mode"] not in valid_mixing_mode:
            errors.append("mixing_mode must be one of: plain, TF, local-TF.")

    if has_param(electrons_params, "startingpot"):
        valid_startingpot = ["atomic", "file"]
        if electrons_params["startingpot"] not in valid_startingpot:
            errors.append("startingpot must be 'atomic' or 'file'.")

    if has_param(electrons_params, "startingwfc"):
        valid_startingwfc = ["atomic", "atomic+random", "random", "file"]
        if electrons_params["startingwfc"] not in valid_startingwfc:
            errors.append(
                "startingwfc must be one of: atomic, atomic+random, random, file."
            )

    if has_param(electrons_params, "diagonalization"):
        valid_diagonalization = ["david", "cg", "paro"]
        if electrons_params["diagonalization"] not in valid_diagonalization:
            errors.append("diagonalization must be one of: david, cg, paro.")

    return errors, warnings


def validate_ions_cell_parameters(calculation, ions_params, cell_params):
    """
    Validate IONS and CELL options currently exposed in the GUI.
    """
    errors = []
    warnings = []
    if calculation == "relax" and not ions_params:
        warnings.append(
            "calculation = 'relax' usually requires the &IONS section. Add &IONS unless you intentionally want to rely on defaults."
        )

    if calculation == "vc-relax":
        if not ions_params:
            warnings.append(
                "calculation = 'vc-relax' usually requires the &IONS section. Add &IONS unless you intentionally want to rely on defaults."
            )

        if not cell_params:
            warnings.append(
                "calculation = 'vc-relax' usually requires the &CELL section. Add &CELL unless you intentionally want to rely on defaults."
            )
            
    valid_ion_positions = ["default", "from_input"]
    valid_ion_velocities = ["default", "from_input"]
    valid_pot_extrapolation = ["atomic", "first_order", "second_order"]
    valid_wfc_extrapolation = ["none", "first_order", "second_order"]

    if ions_params:
        if calculation not in ["relax", "md", "vc-relax", "vc-md"]:
            warnings.append(
                "&IONS is usually used for relax, md, vc-relax, or vc-md calculations."
            )

        if has_param(ions_params, "ion_positions"):
            if ions_params["ion_positions"] not in valid_ion_positions:
                errors.append("ion_positions must be 'default' or 'from_input'.")

        if has_param(ions_params, "ion_velocities"):
            if ions_params["ion_velocities"] not in valid_ion_velocities:
                errors.append("ion_velocities must be 'default' or 'from_input'.")

        if has_param(ions_params, "pot_extrapolation"):
            if ions_params["pot_extrapolation"] not in valid_pot_extrapolation:
                errors.append(
                    "pot_extrapolation must be atomic, first_order, or second_order."
                )

        if has_param(ions_params, "wfc_extrapolation"):
            if ions_params["wfc_extrapolation"] not in valid_wfc_extrapolation:
                errors.append(
                    "wfc_extrapolation must be none, first_order, or second_order."
                )

    if cell_params:
        if calculation not in ["vc-relax", "vc-md"]:
            warnings.append(
                "&CELL is usually used for variable-cell calculations: vc-relax or vc-md."
            )

        if has_param(cell_params, "press_conv_thr"):
            if float(cell_params["press_conv_thr"]) <= 0:
                errors.append("press_conv_thr must be positive.")

        valid_cell_dynamics = ["none", "bfgs", "damp-pr", "damp-w", "pr", "w"]
        if has_param(cell_params, "cell_dynamics"):
            if cell_params["cell_dynamics"] not in valid_cell_dynamics:
                errors.append(
                    "cell_dynamics must be one of: none, bfgs, damp-pr, damp-w, pr, w."
                )

        valid_cell_dofree = [
            "all",
            "ibrav",
            "a",
            "b",
            "c",
            "fixa",
            "fixb",
            "fixc",
            "x",
            "y",
            "z",
            "xy",
            "xz",
            "yz",
            "xyz",
            "shape",
            "volume",
            "2Dxy",
            "2Dshape",
            "epitaxial_ab",
            "epitaxial_ac",
            "epitaxial_bc",
        ]

        if has_param(cell_params, "cell_dofree"):
            cell_dofree = cell_params["cell_dofree"]
            valid_exact = cell_dofree in valid_cell_dofree
            valid_ibrav_combo = cell_dofree.startswith("ibrav+")

            if not valid_exact and not valid_ibrav_combo:
                errors.append(
                    f"Invalid cell_dofree value '{cell_dofree}'. "
                    "Use an official QE option such as all, volume, shape, 2Dxy, or ibrav+option."
                )

    return errors, warnings

def validate_system_settings(ibrav, cell_parameters_text, ecutwfc, ecutrho, calculation):
    """
    Validate or warn about SYSTEM and calculation settings.
    """
    errors = []
    warnings = []

    if ibrav != 0 and cell_parameters_text.strip():
        warnings.append(
            "CELL_PARAMETERS is normally used when ibrav = 0. Since ibrav is not 0, check whether CELL_PARAMETERS is needed."
        )

    if ecutrho < 4 * ecutwfc:
        warnings.append(
            "ecutrho is less than 4 × ecutwfc. For many calculations, ecutrho is commonly at least 4 × ecutwfc, depending on pseudopotentials."
        )

    if calculation == "relax":
        warnings.append(
            "For calculation = 'relax', the &IONS section is included. Check that ion_dynamics is suitable for your calculation."
        )

    if calculation == "vc-relax":
        warnings.append(
            "For calculation = 'vc-relax', the &IONS and &CELL sections are included. Check that ion_dynamics, cell_dynamics, pressure, and cell_dofree are suitable."
        )

    return errors, warnings


def is_number(value):
    """
    Return True if value can be converted to float.
    """
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def has_param(params, key):
    """
    Check if a parameter exists and is not empty.
    """
    return key in params and params[key] is not None and str(params[key]).strip() != ""


def get_lattice_style(system_params):
    """
    Determine whether user is using A/B/C style, celldm style, both, or none.
    """
    abc_keys = ["A", "B", "C", "cosAB", "cosAC", "cosBC"]
    celldm_keys = [
        "celldm(1)",
        "celldm(2)",
        "celldm(3)",
        "celldm(4)",
        "celldm(5)",
        "celldm(6)",
    ]

    used_abc = [key for key in abc_keys if has_param(system_params, key)]
    used_celldm = [key for key in celldm_keys if has_param(system_params, key)]

    return used_abc, used_celldm


def validate_lattice_parameters(system_params, ibrav, use_cell_parameters):
    """
    Validate lattice parameters according to QE ibrav rules.

    Official rule:
    - ibrav = 0: use CELL_PARAMETERS.
    - ibrav != 0: use either celldm(...) or A/B/C/cos..., but not both.
    - Only needed values depending on ibrav should be specified.
    """
    errors = []
    warnings = []

    used_abc, used_celldm = get_lattice_style(system_params)

    # Required A/B/C-style parameters for supported ibrav values.
    # These correspond to QE's A/B/C/cos notation.
    required_abc_by_ibrav = {
        1: ["A"],
        2: ["A"],
        3: ["A"],
        -3: ["A"],
        4: ["A", "C"],
        5: ["A", "cosAB"],
        -5: ["A", "cosAB"],
        6: ["A", "C"],
        7: ["A", "C"],
        8: ["A", "B", "C"],
        9: ["A", "B", "C"],
        -9: ["A", "B", "C"],
        91: ["A", "B", "C"],
        10: ["A", "B", "C"],
        11: ["A", "B", "C"],
        12: ["A", "B", "C", "cosAB"],
        -12: ["A", "B", "C", "cosAC"],
        13: ["A", "B", "C", "cosAB"],
        -13: ["A", "B", "C", "cosAC"],
        14: ["A", "B", "C", "cosAB", "cosAC", "cosBC"],
    }

    allowed_abc_by_ibrav = required_abc_by_ibrav.copy()

    if ibrav == 0:
        if used_abc:
            warnings.append(
                "For ibrav = 0, A/B/C values are optional only for setting alat. "
                "The actual lattice vectors must come from CELL_PARAMETERS."
            )

        if used_celldm:
            warnings.append(
                "For ibrav = 0, only celldm(1) is meaningful if used. "
                "The actual lattice vectors must come from CELL_PARAMETERS."
            )

        if not use_cell_parameters:
            errors.append("CELL_PARAMETERS is required when ibrav = 0.")

        return errors, warnings

    if ibrav not in required_abc_by_ibrav:
        errors.append(
            f"Unsupported or invalid ibrav value: {ibrav}. "
            "Use one of the official QE ibrav values: 0, 1, 2, 3, -3, 4, 5, -5, "
            "6, 7, 8, 9, -9, 91, 10, 11, 12, -12, 13, -13, 14."
        )
        return errors, warnings

    if use_cell_parameters:
        errors.append(
            "CELL_PARAMETERS must be absent when ibrav is not 0. "
            "Use A/B/C/cos... or celldm(...) instead."
        )

    if used_abc and used_celldm:
        errors.append(
            "Do not mix A/B/C/cos... parameters with celldm(...) parameters. "
            "QE requires either celldm(1)-celldm(6) OR A/B/C/cosAB/cosAC/cosBC, not both."
        )

    required_abc = required_abc_by_ibrav[ibrav]
    allowed_abc = allowed_abc_by_ibrav[ibrav]

    if used_abc:
        missing = [key for key in required_abc if key not in used_abc]
        extra = [key for key in used_abc if key not in allowed_abc]

        if missing:
            errors.append(
                f"For ibrav = {ibrav}, the A/B/C style requires: "
                f"{', '.join(required_abc)}. Missing: {', '.join(missing)}."
            )

        if extra:
            errors.append(
                f"For ibrav = {ibrav}, these A/B/C-style parameters are not needed: "
                f"{', '.join(extra)}."
            )

        for key in used_abc:
            if not is_number(system_params[key]):
                errors.append(f"{key} must be numeric.")

    elif used_celldm:
        if not has_param(system_params, "celldm(1)"):
            errors.append("When using celldm(...), celldm(1) is required.")

        for key in used_celldm:
            if not is_number(system_params[key]):
                errors.append(f"{key} must be numeric.")

    else:
        errors.append(
            f"For ibrav = {ibrav}, specify lattice parameters using either "
            "A/B/C/cos... or celldm(...)."
        )

    return errors, warnings

def get_qe_block_title(line):
    """
    Identify QE block/section title from a line.
    """
    stripped = line.strip()

    if stripped.startswith("&CONTROL"):
        return "CONTROL"
    if stripped.startswith("&SYSTEM"):
        return "SYSTEM"
    if stripped.startswith("&ELECTRONS"):
        return "ELECTRONS"
    if stripped.startswith("&IONS"):
        return "IONS"
    if stripped.startswith("&CELL"):
        return "CELL"

    for card_name in [
        "ATOMIC_SPECIES",
        "CELL_PARAMETERS",
        "ATOMIC_POSITIONS",
        "K_POINTS",
    ]:
        if stripped.startswith(card_name):
            return card_name

    return None


def split_qe_input_into_blocks(qe_text):
    """
    Split generated QE input into named blocks.
    """
    blocks = {}
    current_title = None
    current_lines = []

    for line in qe_text.splitlines():
        detected_title = get_qe_block_title(line)

        if detected_title is not None:
            if current_title is not None:
                blocks[current_title] = "\n".join(current_lines).strip()

            current_title = detected_title
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_title is not None:
        blocks[current_title] = "\n".join(current_lines).strip()

    return blocks


def move_item(items, index, direction):
    """
    Move item up or down in a list.
    direction = -1 means up
    direction = 1 means down
    """
    new_items = items.copy()
    new_index = index + direction

    if new_index < 0 or new_index >= len(new_items):
        return new_items

    new_items[index], new_items[new_index] = new_items[new_index], new_items[index]

    return new_items


st.set_page_config(
    page_title="Quantum ESPRESSO Input Generator",
    page_icon="⚛️",
    layout="wide",
)


st.sidebar.title("⚛️ QE Input Generator")

st.sidebar.markdown(
    """
    This app generates Quantum ESPRESSO `pw.x` input files.

    **Workflow**
    1. Fill the input sections
    2. Check validation messages
    3. Preview the generated file
    4. Download the file

    **GitHub**
    - [Input Generator Repo](https://github.com/hrehmaan/qe-input-generator)
    - [Quantum ESPRESSO Docker Environment](https://github.com/hrehmaan/qe-docker)

    **Official documentation**
    - [Quantum ESPRESSO Instructions](https://www.quantum-espresso.org/Doc/INPUT_PW.html)
    - [Source repository](https://gitlab.com/QEF/q-e)
    """
)

st.sidebar.info(
    "This tool checks common formatting mistakes, but it does not guarantee physical correctness."
)

# st.title("⚛️ Quantum ESPRESSO pw.x Input Generator")

# st.markdown(
#     """
#     <div style="
#         padding: 18px;
#         border-radius: 12px;
#         background-color: #f5f7fa;
#         border: 1px solid #e1e4e8;
#         margin-bottom: 25px;
#     ">
#         <h4 style="margin-top: 0;">Generate Quantum ESPRESSO input files without writing them manually</h4>
#         <p style="margin-bottom: 0;">
#             Fill in the GUI fields below, validate the input structure, preview the generated 
#             <code>.pwi</code> file, and download it for use with <code>pw.x</code>.
#         </p>
#     </div>
#     """,
#     unsafe_allow_html=True,
# )

components.html(
    """
    <div style="
        width: 100%;
        min-height: clamp(300px, 42vw, 430px);
        border-radius: 24px;
        overflow: hidden;
        position: relative;
        background:
            radial-gradient(circle at 20% 20%, rgba(56,189,248,0.35), transparent 28%),
            radial-gradient(circle at 80% 30%, rgba(168,85,247,0.28), transparent 30%),
            linear-gradient(135deg, #020617 0%, #0f172a 50%, #111827 100%);
        border: 1px solid rgba(148,163,184,0.35);
        box-shadow: none;
        margin-bottom: 28px;
    ">
        <canvas id="hero-canvas" style="
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
        "></canvas>

        <div style="
            position: relative;
            z-index: 2;
            padding: clamp(18px, 4vw, 36px);
            max-width: 760px;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        ">
            
            <h1 style="
                font-size: clamp(28px, 5vw, 38px);
                line-height: 1.12;
                margin: 0 0 14px 0;
                letter-spacing: -0.03em;
                color: #f8fafc;
            ">
                Quantum ESPRESSO<br>
                <span style="color:#7dd3fc;">
                    pw.x <span style="font-size: clamp(19px, 3.4vw, 26px);">script generator</span> </span>
            </h1>

            <h2 style="
                font-size: clamp(15px, 2.6vw, 19px);
                font-weight: 500;
                color: #cbd5e1;
                margin: 0 0 14px 0;
            ">
                Generate Quantum ESPRESSO input files without writing them manually
            </h2>

            <ul style="
                font-size: clamp(13px, 2.4vw, 16px);
                line-height: 1.55;
                color: #dbeafe;
                margin: 0;
                padding-left: 22px;
                max-width: 700px;
            ">
                <li>Fill the GUI options below.</li>
                <li>Validate the Quantum ESPRESSO input structure.</li>
                <li>Preview and edit the generated input file before downloading.</li>
                <li>Download the final file with any extension, such as <code style="color:#bae6fd;">.pwi</code>, <code style="color:#bae6fd;">.in</code>, or <code style="color:#bae6fd;">.txt</code>, for use with <code style="color:#bae6fd;">pw.x</code>.</li>
            </ul>
        </div>
    </div>

    <script>
    const canvas = document.getElementById("hero-canvas");
    const ctx = canvas.getContext("2d");
    const wrapper = canvas.parentElement;

    function resize() {
        canvas.width = wrapper.offsetWidth;
        canvas.height = wrapper.offsetHeight;
    }

    resize();

    let mouse = { x: canvas.width * 0.75, y: canvas.height * 0.5 };
    let hasMouse = false;

    wrapper.addEventListener("mousemove", function(e) {
        const rect = canvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
        hasMouse = true;
    });

    wrapper.addEventListener("mouseleave", function() {
        hasMouse = false;
    });

    const atoms = [];
    const atomCount = 70;

    for (let i = 0; i < atomCount; i++) {
        atoms.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.55,
            vy: (Math.random() - 0.5) * 0.55,
            r: Math.random() * 2.2 + 1.4
        });
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        for (let i = 0; i < atoms.length; i++) {
            const p = atoms[i];

            p.x += p.vx;
            p.y += p.vy;

            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

            if (hasMouse) {
                const dx = mouse.x - p.x;
                const dy = mouse.y - p.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 150) {
                    p.x -= dx * 0.006;
                    p.y -= dy * 0.006;
                }
            }

            for (let j = i + 1; j < atoms.length; j++) {
                const q = atoms[j];
                const dx = p.x - q.x;
                const dy = p.y - q.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 115) {
                    const opacity = 1 - dist / 115;
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(q.x, q.y);
                    ctx.strokeStyle = `rgba(125, 211, 252, ${opacity * 0.32})`;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(186, 230, 253, 0.92)";
            ctx.fill();

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r * 3.2, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(56, 189, 248, 0.045)";
            ctx.fill();
        }

        requestAnimationFrame(draw);
    }

    draw();

    window.addEventListener("resize", resize);
    </script>
    """,
    height=430,
)

# -----------------------------
# CONTROL SECTION
# -----------------------------

st.header("1. CONTROL section")

col1, col2 = st.columns(2)

with col1:
    calculation = st.selectbox(
        "calculation",
        ["scf", "relax", "vc-relax", "nscf", "bands"],
        index=0,
        help="Type of calculation to perform.",
    )

    pseudo_dir = st.text_input(
        "pseudo_dir",
        value="./",
        help="Folder where pseudopotential files are located.",
    )

with col2:
    prefix = st.text_input(
        "prefix",
        value="qe",
        help="Prefix used for output files.",
    )

    outdir = st.text_input(
        "outdir",
        value="./tmp/",
        help="Temporary directory for QE output files.",
    )


control_params = {
    "calculation": calculation,
    "pseudo_dir": pseudo_dir,
    "prefix": prefix,
    "outdir": outdir,
}


with st.expander("Optional CONTROL parameters", expanded=False):
    use_verbosity = st.checkbox("Add verbosity")
    if use_verbosity:
        control_params["verbosity"] = st.selectbox(
            "verbosity",
            ["low", "high"],
            index=1,
            help="Amount of output printed by Quantum ESPRESSO.",
        )

    use_restart_mode = st.checkbox("Add restart_mode")
    if use_restart_mode:
        control_params["restart_mode"] = st.selectbox(
            "restart_mode",
            ["from_scratch", "restart"],
            index=0,
            help="Use from_scratch for a new calculation.",
        )

    use_max_seconds = st.checkbox("Add max_seconds")
    if use_max_seconds:
        control_params["max_seconds"] = st.number_input(
            "max_seconds",
            min_value=1.0,
            value=3600.0,
            step=100.0,
            help="Maximum wall time in seconds.",
        )

    use_wf_collect = st.checkbox("Add wf_collect")
    if use_wf_collect:
        st.warning(
            "wf_collect is obsolete in recent Quantum ESPRESSO versions. Use only if you know you need it."
        )
        control_params["wf_collect"] = st.checkbox(
            "wf_collect value",
            value=True,
        )

    use_etot_conv_thr = st.checkbox("Add etot_conv_thr")
    if use_etot_conv_thr:
        control_params["etot_conv_thr"] = st.number_input(
            "etot_conv_thr",
            value=1.0e-4,
            format="%.1e",
            help="Total energy convergence threshold.",
        )

    use_forc_conv_thr = st.checkbox("Add forc_conv_thr")
    if use_forc_conv_thr:
        control_params["forc_conv_thr"] = st.number_input(
            "forc_conv_thr",
            value=1.0e-3,
            format="%.1e",
            help="Force convergence threshold.",
        )

st.divider()

# -----------------------------
# SYSTEM SECTION
# -----------------------------

st.header("2. SYSTEM section")

col1, col2, col3 = st.columns(3)

with col1:
    ibrav = st.number_input(
        "ibrav",
        value=0,
        step=1,
        help="Bravais lattice index. Use 0 when CELL_PARAMETERS are given manually.",
    )

    nat = st.number_input(
        "nat",
        min_value=1,
        value=5,
        step=1,
        help="Number of atoms in the unit cell.",
    )

with col2:
    ntyp = st.number_input(
        "ntyp",
        min_value=1,
        value=3,
        step=1,
        help="Number of atomic species.",
    )

    ecutwfc = st.number_input(
        "ecutwfc",
        min_value=0.0,
        value=30.0,
        step=5.0,
        help="Plane-wave kinetic energy cutoff.",
    )

with col3:
    ecutrho = st.number_input(
        "ecutrho",
        min_value=0.0,
        value=240.0,
        step=10.0,
        help="Charge density cutoff.",
    )


system_params = {
    "ibrav": ibrav,
    "nat": nat,
    "ntyp": ntyp,
    "ecutwfc": ecutwfc,
    "ecutrho": ecutrho,
}


with st.expander("Optional SYSTEM: lattice parameters", expanded=False):
    
    with st.expander("Optional SYSTEM: lattice parameters", expanded=False):
        use_A = st.checkbox("Add A")
        if use_A:
            system_params["A"] = st.number_input(
                "A",
                value=4.41813,
                step=0.01,
                help="Lattice parameter A in Angstrom.",
            )

        use_B = st.checkbox("Add B")
        if use_B:
            system_params["B"] = st.number_input(
                "B",
                value=0.0,
                step=0.01,
                help="Lattice parameter B in Angstrom. Only needed for some ibrav values.",
            )

        use_C = st.checkbox("Add C")
        if use_C:
            system_params["C"] = st.number_input(
                "C",
                value=32.2573,
                step=0.01,
                help="Lattice parameter C in Angstrom.",
            )

        use_cosAB = st.checkbox("Add cosAB")
        if use_cosAB:
            system_params["cosAB"] = st.number_input("cosAB", value=0.0, step=0.01)

        use_cosAC = st.checkbox("Add cosAC")
        if use_cosAC:
            system_params["cosAC"] = st.number_input("cosAC", value=0.0, step=0.01)

        use_cosBC = st.checkbox("Add cosBC")
        if use_cosBC:
            system_params["cosBC"] = st.number_input("cosBC", value=0.0, step=0.01)

    use_celldm = st.checkbox("Add celldm(1) to celldm(6)")
    if use_celldm:
        col1, col2, col3 = st.columns(3)

        with col1:
            system_params["celldm(1)"] = st.number_input("celldm(1)", value=0.0)
            system_params["celldm(2)"] = st.number_input("celldm(2)", value=0.0)

        with col2:
            system_params["celldm(3)"] = st.number_input("celldm(3)", value=0.0)
            system_params["celldm(4)"] = st.number_input("celldm(4)", value=0.0)

        with col3:
            system_params["celldm(5)"] = st.number_input("celldm(5)", value=0.0)
            system_params["celldm(6)"] = st.number_input("celldm(6)", value=0.0)


with st.expander("Optional SYSTEM: charge settings", expanded=False):
    use_tot_charge = st.checkbox("Add tot_charge")
    if use_tot_charge:
        system_params["tot_charge"] = st.number_input(
            "tot_charge",
            value=0.0,
            step=0.1,
            help="Total charge of the system.",
        )

    use_starting_charge = st.checkbox("Add starting_charge")
    if use_starting_charge:
        st.info(
            "For now this adds starting_charge(1). Later we can make this dynamic for all atomic species."
        )
        system_params["starting_charge(1)"] = st.number_input(
            "starting_charge(1)",
            value=0.0,
            step=0.1,
        )


with st.expander("Optional SYSTEM: symmetry settings", expanded=False):
    use_nosym = st.checkbox("Add nosym")
    if use_nosym:
        system_params["nosym"] = st.checkbox("nosym value", value=True)

    use_noinv = st.checkbox("Add noinv")
    if use_noinv:
        system_params["noinv"] = st.checkbox("noinv value", value=True)


with st.expander("Optional SYSTEM: bands and DFT settings", expanded=False):
    use_nbnd = st.checkbox("Add nbnd")
    if use_nbnd:
        system_params["nbnd"] = st.number_input(
            "nbnd",
            min_value=1,
            value=20,
            step=1,
            help="Number of electronic bands.",
        )

    use_input_dft = st.checkbox("Add input_dft")
    if use_input_dft:
        system_params["input_dft"] = st.text_input(
            "input_dft",
            value="PBE",
            help="Exchange-correlation functional, e.g. PBE.",
        )


with st.expander("Optional SYSTEM: spin settings", expanded=False):
    use_nspin = st.checkbox("Add nspin")
    if use_nspin:
        system_params["nspin"] = st.selectbox(
            "nspin",
            [1, 2],
            index=0,
            help="1 = non-spin-polarized, 2 = spin-polarized. Noncollinear calculations will be added later.",
        )


with st.expander("Optional SYSTEM: occupations and smearing", expanded=False):
    use_occupations = st.checkbox("Add occupations")
    if use_occupations:
        occupations = st.selectbox(
            "occupations",
            ["fixed", "smearing", "tetrahedra", "tetrahedra_lin", "tetrahedra_opt", "from_input"],
            index=0,
        )
        system_params["occupations"] = occupations

        if occupations == "smearing":
            system_params["smearing"] = st.selectbox(
                "smearing",
                [
                    "gaussian",
                    "gauss",
                    "methfessel-paxton",
                    "m-p",
                    "mp",
                    "marzari-vanderbilt",
                    "cold",
                    "m-v",
                    "mv",
                    "fermi-dirac",
                    "f-d",
                    "fd",
                ],
                index=0,
            )

            system_params["degauss"] = st.number_input(
                "degauss",
                min_value=0.0,
                value=0.01,
                step=0.001,
                format="%.6f",
            )

st.divider()

# -----------------------------
# ELECTRONS SECTION
# -----------------------------

st.header("3. ELECTRONS section")

col1, col2 = st.columns(2)

with col1:
    conv_thr = st.number_input(
        "conv_thr",
        min_value=0.0,
        value=1.0e-6,
        format="%.1e",
        help="Self-consistency convergence threshold.",
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


electrons_params = {
    "conv_thr": conv_thr,
    "mixing_beta": mixing_beta,
}


with st.expander("Optional ELECTRONS parameters", expanded=False):
    use_electron_maxstep = st.checkbox("Add electron_maxstep")
    if use_electron_maxstep:
        electrons_params["electron_maxstep"] = st.number_input(
            "electron_maxstep",
            min_value=1,
            value=100,
            step=10,
            help="Maximum number of electronic SCF steps.",
        )

    use_mixing_mode = st.checkbox("Add mixing_mode")
    if use_mixing_mode:
        electrons_params["mixing_mode"] = st.selectbox(
            "mixing_mode",
            ["plain", "TF", "local-TF"],
            index=0,
        )

    use_startingpot = st.checkbox("Add startingpot")
    if use_startingpot:
        electrons_params["startingpot"] = st.selectbox(
            "startingpot",
            ["atomic", "file"],
            index=0,
        )

    use_startingwfc = st.checkbox("Add startingwfc")
    if use_startingwfc:
        electrons_params["startingwfc"] = st.selectbox(
            "startingwfc",
            ["atomic", "atomic+random", "random", "file"],
            index=1,
            help="Initial wavefunction guess.",
        )

    use_scf_must_converge = st.checkbox("Add scf_must_converge")
    if use_scf_must_converge:
        electrons_params["scf_must_converge"] = st.checkbox(
            "scf_must_converge value",
            value=True,
        )

    use_diagonalization = st.checkbox("Add diagonalization")
    if use_diagonalization:
        electrons_params["diagonalization"] = st.selectbox(
            "diagonalization",
            ["david", "cg", "paro"],
            index=0,
        )

st.divider()

# -----------------------------
# IONS AND CELL SECTION
# -----------------------------

st.header("4. IONS and CELL section")

ions_params = {}
cell_params = {}

recommended_ions = calculation in ["relax", "vc-relax"]
recommended_cell = calculation == "vc-relax"

use_ions = st.checkbox(
    "Add &IONS section",
    value=recommended_ions,
    help="Recommended for relax and vc-relax calculations.",
)

if use_ions:
    with st.expander("&IONS parameters", expanded=True):
        use_ion_dynamics = st.checkbox("Add ion_dynamics", value=True)
        if use_ion_dynamics:
            ions_params["ion_dynamics"] = st.selectbox(
                "ion_dynamics",
                ["bfgs", "damp", "verlet"],
                index=0,
            )

        use_ion_positions = st.checkbox("Add ion_positions")
        if use_ion_positions:
            ions_params["ion_positions"] = st.selectbox(
                "ion_positions",
                ["default", "from_input"],
                index=0,
            )

        use_ion_velocities = st.checkbox("Add ion_velocities")
        if use_ion_velocities:
            ions_params["ion_velocities"] = st.selectbox(
                "ion_velocities",
                ["default", "from_input"],
                index=0,
            )

        use_pot_extrapolation = st.checkbox("Add pot_extrapolation")
        if use_pot_extrapolation:
            ions_params["pot_extrapolation"] = st.selectbox(
                "pot_extrapolation",
                ["atomic", "first_order", "second_order"],
                index=0,
            )

        use_wfc_extrapolation = st.checkbox("Add wfc_extrapolation")
        if use_wfc_extrapolation:
            ions_params["wfc_extrapolation"] = st.selectbox(
                "wfc_extrapolation",
                ["none", "first_order", "second_order"],
                index=0,
            )

use_cell = st.checkbox(
    "Add &CELL section",
    value=recommended_cell,
    help="Recommended for vc-relax calculations.",
)

if use_cell:
    with st.expander("&CELL parameters", expanded=True):
        use_cell_dynamics = st.checkbox("Add cell_dynamics", value=True)
        if use_cell_dynamics:
            cell_params["cell_dynamics"] = st.selectbox(
                "cell_dynamics",
                ["bfgs", "damp-pr", "damp-w"],
                index=0,
            )

        use_cell_dofree = st.checkbox("Add cell_dofree")
        if use_cell_dofree:
            cell_params["cell_dofree"] = st.selectbox(
                "cell_dofree",
                [
                    "all",
                    "ibrav",
                    "a",
                    "b",
                    "c",
                    "fixa",
                    "fixb",
                    "fixc",
                    "x",
                    "y",
                    "z",
                    "xy",
                    "xz",
                    "yz",
                    "xyz",
                    "shape",
                    "volume",
                    "2Dxy",
                    "2Dshape",
                    "epitaxial_ab",
                    "epitaxial_ac",
                    "epitaxial_bc",
                ],
                index=0,
            )

        use_press_conv_thr = st.checkbox("Add press_conv_thr")
        if use_press_conv_thr:
            cell_params["press_conv_thr"] = st.number_input(
                "press_conv_thr",
                value=0.5,
                step=0.1,
                help="Pressure convergence threshold.",
            )

st.divider()

# -----------------------------
# ATOMIC SPECIES
# -----------------------------

st.markdown(
    """
    <div class="qe-section-card">
        <h3>5. ATOMIC_SPECIES section</h3>
        <p>List each atomic species, atomic mass, and pseudopotential file.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Pseudopotential filenames are suggestions only. Make sure the selected files exist in your pseudo_dir and are suitable for your calculation."
)

use_atomic_species_helper = st.checkbox(
    "Use ATOMIC_SPECIES helper",
    value=False,
    help="Automatically build ATOMIC_SPECIES from selected elements and pseudopotential filenames.",
)

if use_atomic_species_helper:
    element_text = st.text_input(
        "Elements",
        value="Ba Ti O",
        help="Enter element symbols separated by spaces or commas, for example: Ba Ti O",
        key="atomic_species_helper_elements",
    )

    selected_elements = parse_element_list(element_text)
    selected_pseudos = {}

    if selected_elements:
        st.caption("Select pseudopotential filename for each element.")

        for element in selected_elements:
            mass = ATOMIC_MASSES.get(element)

            if mass is None:
                st.warning(
                    f"Atomic mass for {element} is not in the built-in table. Please edit the generated text manually."
                )
            else:
                st.write(f"**{element}** atomic mass: `{mass}`")

            pseudo_options = PSEUDO_SUGGESTIONS.get(element, [f"{element}.upf"])
            pseudo_options_with_other = pseudo_options + ["Other / custom filename"]

            pseudo_choice = st.selectbox(
                f"{element} suggested pseudopotential file",
                pseudo_options_with_other,
                index=0,
                key=f"pseudo_choice_{element}",
            )

            if pseudo_choice == "Other / custom filename":
                selected_pseudos[element] = st.text_input(
                    f"{element} custom pseudopotential filename",
                    value=f"{element}.UPF",
                    key=f"pseudo_custom_{element}",
                    help="Type the exact pseudopotential filename available in your pseudo_dir.",
                )
            else:
                selected_pseudos[element] = pseudo_choice

    generated_atomic_species = build_atomic_species_text(
        selected_elements=selected_elements,
        selected_pseudos=selected_pseudos,
    )

    atomic_species_key = "generated_atomic_species_" + str(
        abs(hash(generated_atomic_species))
    )

    atomic_species = st.text_area(
        "Generated ATOMIC_SPECIES",
        value=generated_atomic_species,
        height=140,
        help="You can edit the generated ATOMIC_SPECIES text before generating the final input.",
        key=atomic_species_key,
    )

else:
    atomic_species = st.text_area(
        "Enter atomic species manually",
        value="""Ba 137.327 Ba.upf
Ti 47.867 Ti.upf
O 15.999 O.upf""",
        height=120,
        help="Format: Element AtomicMass PseudopotentialFile",
        key="manual_atomic_species_text_area",
    )

st.caption("Example format: `Ba 137.327 Ba.upf`")

st.divider()

# -----------------------------
# CELL PARAMETERS
# -----------------------------

st.header("5. CELL_PARAMETERS section")

use_cell_parameters_default = ibrav == 0

use_cell_parameters = st.checkbox(
    "Add CELL_PARAMETERS card",
    value=use_cell_parameters_default,
    help="Required when ibrav = 0. Must be absent when ibrav is not 0.",
)

cell_parameters_type = "angstrom"
cell_parameters = ""

if use_cell_parameters:
    cell_parameters_type = st.selectbox(
        "CELL_PARAMETERS type",
        ["angstrom", "bohr", "alat"],
        index=0,
        help="Units/type for CELL_PARAMETERS.",
    )

    cell_parameters = st.text_area(
        "Enter cell parameters",
        value="""4.00768164000000 0.00000000000000 0.00000000000000
0.00000000000000 4.00768164000000 0.00000000000000
0.00000000000000 0.00000000000000 4.00768164000000""",
        height=130,
        help="Three lattice vectors. Each row should contain x y z values.",
    )
else:
    st.info("CELL_PARAMETERS will not be printed.")

    
st.divider()
# -----------------------------
# ATOMIC POSITIONS
# -----------------------------

st.header("6. ATOMIC_POSITIONS section")

atomic_positions_type = st.selectbox(
    "ATOMIC_POSITIONS type",
    ["angstrom", "crystal", "bohr", "alat", "crystal_sg"],
    index=0,
    help="Coordinate type for ATOMIC_POSITIONS.",
)

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

st.divider()
# -----------------------------
# K POINTS
# -----------------------------

# -----------------------------
# K POINTS
# -----------------------------

st.header("7. K_POINTS section")

k_points_type = st.selectbox(
    "K_POINTS type",
    [
        "automatic",
        "gamma",
        "crystal",
        "tpiba",
        "crystal_b",
        "tpiba_b",
        "crystal_c",
        "tpiba_c",
    ],
    index=0,
    help="Choose the K_POINTS format.",
)


k_points = st.text_area(
    "Enter K_POINTS values",
    value="4 4 4 0 0 0",
    height=120,
    help=(
        "automatic: kx ky kz sx sy sz\n"
        "gamma: leave empty\n"
        "crystal/tpiba/crystal_b/tpiba_b/crystal_c/tpiba_c: first line is number of k-points, followed by k-point rows."
    ),
)


st.divider()

# -----------------------------
# GENERATE INPUT FILE
# -----------------------------

qe_input = generate_qe_input(
    control_params=control_params,
    system_params=system_params,
    electrons_params=electrons_params,
    ions_params=ions_params,
    cell_params=cell_params,
    atomic_species=atomic_species,
    cell_parameters=cell_parameters,
    atomic_positions=atomic_positions,
    atomic_positions_type=atomic_positions_type,
    cell_parameters_type=cell_parameters_type,
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

cell_errors, cell_warnings = validate_cell_parameters(
    cell_parameters_text=cell_parameters,
    ibrav=ibrav,
    use_cell_parameters=use_cell_parameters,
)

position_errors, position_warnings = validate_atomic_positions(
    atomic_positions_text=atomic_positions,
    expected_nat=nat,
    atomic_species_text=atomic_species,
)

kpoint_errors, kpoint_warnings = validate_k_points(
    k_points_type=k_points_type,
    k_points_text=k_points,
)

control_errors, control_warnings = validate_control_parameters(
    control_params=control_params,
)

system_param_errors, system_param_warnings = validate_system_parameters(
    system_params=system_params,
    ibrav=ibrav,
    use_cell_parameters=use_cell_parameters,
)

electrons_errors, electrons_warnings = validate_electrons_parameters(
    electrons_params=electrons_params,
)

ions_cell_errors, ions_cell_warnings = validate_ions_cell_parameters(
    calculation=calculation,
    ions_params=ions_params,
    cell_params=cell_params,
)

validation_errors.extend(species_errors)
validation_errors.extend(cell_errors)
validation_errors.extend(position_errors)
validation_errors.extend(kpoint_errors)
validation_errors.extend(control_errors)
validation_errors.extend(system_param_errors)
validation_errors.extend(electrons_errors)
validation_errors.extend(ions_cell_errors)


validation_warnings.extend(species_warnings)
validation_warnings.extend(cell_warnings)
validation_warnings.extend(position_warnings)
validation_warnings.extend(kpoint_warnings)
validation_warnings.extend(control_warnings)
validation_warnings.extend(system_param_warnings)
validation_warnings.extend(electrons_warnings)
validation_warnings.extend(ions_cell_warnings)


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
    st.error("Some required input rules are not satisfied. Please fix the following error(s):")

    for error in validation_errors:
        st.write(f"❌ {error}")
else:
    st.success("No critical formatting errors detected. The file structure looks consistent.")

if validation_warnings:
    st.warning("The input can still be generated, but please review these warning(s):")

    for warning in validation_warnings:
        st.write(f"⚠️ {warning}")

st.divider()

# -----------------------------
# SHOW PREVIEW
# -----------------------------

st.header("9. 📄 Generated input preview")

st.caption(
    "You can reorder selected sections using the arrow buttons below, then manually edit the final input before downloading."
)

# st.warning(
#     "Manual edits and section reordering are allowed. Make sure the final input follows the official QE order and syntax."
# )

qe_blocks = split_qe_input_into_blocks(qe_input)

fixed_namelist_order = [
    "CONTROL",
    "SYSTEM",
    "ELECTRONS",
    "IONS",
    "CELL",
]

movable_card_sections = [
    section
    for section in [
        "ATOMIC_SPECIES",
        "CELL_PARAMETERS",
        "ATOMIC_POSITIONS",
        "K_POINTS",
    ]
    if section in qe_blocks
]

if "card_order" not in st.session_state:
    st.session_state.card_order = movable_card_sections

if "last_qe_input" not in st.session_state:
    st.session_state.last_qe_input = qe_input

if st.session_state.last_qe_input != qe_input:
    st.session_state.card_order = movable_card_sections
    st.session_state.last_qe_input = qe_input


ordered_blocks = []

for section_name in fixed_namelist_order:
    if section_name in qe_blocks:
        ordered_blocks.append(qe_blocks[section_name])

for section_name in st.session_state.card_order:
    if section_name in qe_blocks:
        ordered_blocks.append(qe_blocks[section_name])

reordered_qe_input = "\n\n".join(ordered_blocks).strip() + "\n"

final_qe_input = st.text_area(
    "Editable final Quantum ESPRESSO input",
    value=reordered_qe_input,
    height=500,
    help="This exact text will be downloaded.",
)

show_section_mover = st.checkbox(
    "Do you want to move sections up or down?",
    value=False,
    help="Enable this only if you want to reorder ATOMIC_SPECIES, CELL_PARAMETERS, ATOMIC_POSITIONS, or K_POINTS in the final preview.",
)

if show_section_mover:
    st.markdown(
        "<p style='font-size: 13px; color: #64748b; margin-top: 8px; margin-bottom: 4px;'>Move card sections up or down</p>",
        unsafe_allow_html=True,
    )

    for i, section_name in enumerate(st.session_state.card_order):
        col1, col2, col3 = st.columns([0.45, 3.5, 0.45])

        with col1:
            if st.button("▲", key=f"move_up_{section_name}", disabled=(i == 0)):
                st.session_state.card_order = move_item(
                    st.session_state.card_order,
                    i,
                    -1,
                )
                st.rerun()

        with col2:
            st.markdown(
                f"<span style='font-size: 13px; color: #475569;'>{i + 1}. {section_name}</span>",
                unsafe_allow_html=True,
            )

        with col3:
            if st.button("▼", key=f"move_down_{section_name}", disabled=(i == len(st.session_state.card_order) - 1)):
                st.session_state.card_order = move_item(
                    st.session_state.card_order,
                    i,
                    1,
                )
                st.rerun()
st.divider()

# -----------------------------
# DOWNLOAD FILE
# -----------------------------

st.header("10. ⬇️ Download file")
st.caption("Choose the output file name and download the generated input file.")
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
    data=final_qe_input,
    file_name=output_file_name,
    mime="text/plain",
    key="download_qe_input_file",
    disabled=download_disabled,
)

st.divider()

st.markdown(
    """
    <div style="text-align: center; color: gray; font-size: 0.9em;">
        Built for generating beginner-friendly Quantum ESPRESSO pw.x input files.
    </div>
    """,
    unsafe_allow_html=True,
)