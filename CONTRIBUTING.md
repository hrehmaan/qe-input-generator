# Contributing

Thank you for your interest in contributing to **QE Input PWI Generator**.

This project provides a browser-based GUI for generating Quantum ESPRESSO `pw.x` input files. Contributions are welcome, especially improvements related to Quantum ESPRESSO input syntax, validation, usability, documentation, examples, and testing.

## Before contributing

Before making a large change, please open a GitHub issue first. This helps discuss the bug, missing feature, or improvement before work begins.

Good issue topics include:

- Bug in the generated Quantum ESPRESSO input file
- Missing `pw.x` parameter
- Incorrect validation rule
- New validation rule based on official QE documentation
- GUI usability improvement
- Mobile responsiveness issue
- Documentation improvement
- Example input file request
- Streamlit deployment issue

Official Quantum ESPRESSO input documentation should be used as the main reference:

https://www.quantum-espresso.org/Doc/INPUT_PW.html

## Project goals

The goal of this project is to make Quantum ESPRESSO input generation easier for beginners while still following official `pw.x` syntax as closely as possible.

The app should:

- Generate readable Quantum ESPRESSO input files
- Allow users to select only the parameters they need
- Avoid printing unnecessary variables
- Validate common formatting mistakes
- Support official `pw.x` namelists and cards step by step
- Keep the interface simple for non-programmers
- Allow advanced users to manually edit the final input before downloading

## Development setup

Clone the repository:

```bash
git clone https://github.com/hrehmaan/qe-input-generator.git
cd qe-input-generator