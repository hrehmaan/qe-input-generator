
import streamlit as st

from qe_generator import generate_qe_input
import streamlit.components.v1 as components

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
            values = []

            for value in parts:
                try:
                    values.append(int(value))
                except ValueError:
                    errors.append(
                        f"K_POINTS automatic value '{value}' should be an integer."
                    )

            if len(values) == 6:
                k1, k2, k3, s1, s2, s3 = values

                if k1 <= 0 or k2 <= 0 or k3 <= 0:
                    errors.append(
                        "K_POINTS automatic grid values kx, ky, kz should be positive integers."
                    )

                for shift in [s1, s2, s3]:
                    if shift not in [0, 1]:
                        errors.append(
                            "K_POINTS automatic shift values sx, sy, sz should be only 0 or 1."
                        )
                        break

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

    **Official documentation**

    [Quantum ESPRESSO INPUT_PW](https://www.quantum-espresso.org/Doc/INPUT_PW.html)
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
            [1, 2, 4],
            index=0,
            help="1 = non-spin-polarized, 2 = spin-polarized, 4 = noncollinear.",
        )


with st.expander("Optional SYSTEM: occupations and smearing", expanded=False):
    use_occupations = st.checkbox("Add occupations")
    if use_occupations:
        occupations = st.selectbox(
            "occupations",
            ["fixed", "smearing", "tetrahedra", "tetrahedra_opt"],
            index=0,
        )
        system_params["occupations"] = occupations

        if occupations == "smearing":
            system_params["smearing"] = st.selectbox(
                "smearing",
                [
                    "gaussian",
                    "methfessel-paxton",
                    "marzari-vanderbilt",
                    "fermi-dirac",
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
                ["all", "x", "y", "z", "xy", "xz", "yz", "xyz", "shape", "volume", "2Dxy"],
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

system_errors, system_warnings = validate_system_settings(
    ibrav=ibrav,
    cell_parameters_text=cell_parameters,
    ecutwfc=ecutwfc,
    ecutrho=ecutrho,
    calculation=calculation,
)

validation_errors.extend(species_errors)
validation_errors.extend(cell_errors)
validation_errors.extend(position_errors)
validation_errors.extend(kpoint_errors)
validation_errors.extend(system_errors)

validation_warnings.extend(species_warnings)
validation_warnings.extend(cell_warnings)
validation_warnings.extend(position_warnings)
validation_warnings.extend(kpoint_warnings)
validation_warnings.extend(system_warnings)


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
    "You can reorder selected card sections using the arrow buttons, then manually edit the final input before downloading."
)

st.warning(
    "Manual edits and section reordering are allowed. Make sure the final input follows the official QE order and syntax."
)

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

st.subheader("Move card sections up or down")

for i, section_name in enumerate(st.session_state.card_order):
    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        if st.button("▲", key=f"move_up_{section_name}", disabled=(i == 0)):
            st.session_state.card_order = move_item(
                st.session_state.card_order,
                i,
                -1,
            )
            st.rerun()

    with col2:
        st.write(f"**{i + 1}. {section_name}**")

    with col3:
        if st.button("▼", key=f"move_down_{section_name}", disabled=(i == len(st.session_state.card_order) - 1)):
            st.session_state.card_order = move_item(
                st.session_state.card_order,
                i,
                1,
            )
            st.rerun()

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