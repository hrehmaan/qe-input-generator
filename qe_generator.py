"""
Quantum ESPRESSO pw.x input generator.

This module builds input files from selected parameters.
Only parameters provided by the GUI are printed.
"""


def bool_to_qe(value):
    """Convert Python True/False to Quantum ESPRESSO .true. / .false."""
    return ".true." if value else ".false."


def format_qe_value(value):
    """Format Python values for Quantum ESPRESSO input syntax."""
    if isinstance(value, bool):
        return bool_to_qe(value)

    if isinstance(value, str):
        return f"'{value}'"

    return value


def build_namelist(name, parameters):
    """
    Build a Quantum ESPRESSO namelist.

    Empty strings and None values are skipped.
    """
    lines = [f"&{name}"]

    for key, value in parameters.items():
        if value is None:
            continue

        if isinstance(value, str) and value.strip() == "":
            continue

        lines.append(f"    {key} = {format_qe_value(value)}")

    lines.append("/")
    return "\n".join(lines)


def generate_qe_input(
    control_params,
    system_params,
    electrons_params,
    atomic_species,
    atomic_positions,
    k_points_type,
    k_points,
    ions_params=None,
    cell_params=None,
    cell_parameters=None,
    atomic_positions_type="angstrom",
    cell_parameters_type="angstrom",
):
    """
    Generate a Quantum ESPRESSO pw.x input file as text.

    Namelist order follows the official pw.x input structure:
    CONTROL, SYSTEM, ELECTRONS, optional IONS, optional CELL, then cards.
    """

    ions_params = ions_params or {}
    cell_params = cell_params or {}

    sections = []

    sections.append(build_namelist("CONTROL", control_params))
    sections.append(build_namelist("SYSTEM", system_params))
    sections.append(build_namelist("ELECTRONS", electrons_params))

    if ions_params:
        sections.append(build_namelist("IONS", ions_params))

    if cell_params:
        sections.append(build_namelist("CELL", cell_params))

    sections.append(f"ATOMIC_SPECIES\n{atomic_species.strip()}")

    if cell_parameters and cell_parameters.strip():
        sections.append(
            f"CELL_PARAMETERS {cell_parameters_type}\n{cell_parameters.strip()}"
        )

    sections.append(
        f"ATOMIC_POSITIONS {atomic_positions_type}\n{atomic_positions.strip()}"
    )

    if k_points_type == "gamma":
        sections.append("K_POINTS gamma")
    else:
        sections.append(f"K_POINTS {k_points_type}\n{k_points.strip()}")

    return "\n\n".join(sections) + "\n"