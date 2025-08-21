# rew2streammagic

rew2streammagic is a Python tool to parse Room EQ Wizard (REW) equalizer description files (Equalizer APO file format) and apply the extracted equalizer settings to Cambridge Audio StreamMagic devices.

## Features

- Parse REW filter files and extract the first seven equalizer bands
- Supports various filter types (PEAKING, LOWSHELF, HIGHSHELF, LOWPASS, HIGHPASS)
- Maps REW filter types to StreamMagic-compatible types
- Communicates with StreamMagic devices to set user EQ parameters

## Usage

1. Prepare a REW filter file (see `example_data/` for samples).

1. Install dependencies

    ```sh
    poetry install
    ```

1. Run the tool:

    ```sh
    poetry run rew2streammagic <path_to_eq_file>
    ```

1. The tool will parse the file and send the EQ settings to your StreamMagic device, if it is supported by the API version.

## Example

See the `example_data/` folder for sample input files.

## Requirements

> [!WARNING]
> The changes required for equalizer support are not yet released in aiostreammagic and are only available in this [feature branch](https://github.com/Solmath/aiostreammagic/tree/feature/add-eq-support)

- Python 3.11+
- [aiostreammagic](https://github.com/noahhusby/aiostreammagic)
- poetry (for development)
