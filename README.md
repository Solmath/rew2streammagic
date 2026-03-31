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

1. The tool will parse the file and send the EQ settings to your StreamMagic device at the specified host IP address, if it is supported by the API version.

## Advanced options

- IP adress of the host can be set with the ```--host``` argument

    ```sh
    poetry run rew2streammagic <path_to_eq_file> --host 192.168.1.50
    ````

  IP adresses will be validated before attempting connection to ensure proper format.

- To check whether the file can be parsed without connecting to the device:

    ```sh
    poetry run rew2streammagic <path_to_eq_file> --dry-run
    ```

- Duration of the connection timeout in seconds can be set like this:

    ```sh
    poetry run rew2streammagic <path_to_eq_file> --timeout 10
    ```

## Example

See the `example_data/` folder for sample input files.

## Requirements

> [!WARNING]
> The changes required for equalizer support are not yet released in aiostreammagic and are only available in this [feature branch](https://github.com/Solmath/aiostreammagic/tree/feature/add-eq-support)

- Python 3.11+
- [aiostreammagic](https://github.com/noahhusby/aiostreammagic)
- poetry (for development)
