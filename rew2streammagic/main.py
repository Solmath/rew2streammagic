"""
Main entry point for parsing a Room EQ Wizard (REW) equalizer description file
and extracting the first seven equalizer band settings.
"""

import sys
import re
import asyncio
import logging
from pathlib import Path
from aiohttp import (
    ClientSession,
    ClientConnectorError,
    ClientError,
    ClientTimeout,
    ServerTimeoutError,
)
from aiostreammagic import StreamMagicClient, EQBand, UserEQ, EQFilterType, Info
from packaging.version import Version

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_eq_file(file_path):
    """Parse EQ file and return UserEQ object with band settings."""
    bands = []
    filter_map = {
        "LS": "LOWSHELF",
        "PK": "PEAKING",
        "HS": "HIGHSHELF",
        "LP": "LOWPASS",
        "HP": "HIGHPASS",
    }
    band_pattern = re.compile(
        r"^Filter\s+(\d+):\s+ON\s+([A-Z]+)\s+Fc\s+([\d.]+)\s*Hz(?:\s+Gain\s+([\-\d.]+)\s*dB)?(?:\s+Q\s+([\d.]+))?"
    )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                match = band_pattern.match(line.strip())
                if match:
                    band_num = int(match.group(1)) - 1  # zero-based index
                    filter_type = match.group(2)
                    freq = float(match.group(3))
                    gain = float(match.group(4)) if match.group(4) is not None else None
                    q = float(match.group(5)) if match.group(5) is not None else None
                    mapped_filter = filter_map.get(filter_type, filter_type)

                    try:
                        band = EQBand(
                            index=band_num,
                            filter=EQFilterType[mapped_filter],
                            freq=int(freq),
                            gain=gain,
                            q=q,
                        )
                        bands.append(band)
                        if len(bands) == 7:
                            break
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Skipping invalid band {band_num}: {e}")
                        continue
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except IOError as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing file {file_path}: {e}")
        raise

    return UserEQ(bands=bands)


async def connect_and_apply_eq(host, user_eq, timeout=10):
    """Connect to StreamMagic device and apply EQ settings."""
    try:
        # Create session with timeout
        timeout_config = ClientTimeout(total=timeout)
        async with ClientSession(timeout=timeout_config) as session:
            logger.info(f"Attempting to connect to {host}")
            client = StreamMagicClient(host, session=session)

            try:
                await client.connect()
                logger.info(f"Successfully connected to {host}")

                # Get device info
                try:
                    info: Info = await client.get_info()
                    logger.info(f"Device API version: {info.api_version}")

                    if Version(info.api_version) >= Version("1.9"):
                        logger.info("Applying EQ settings...")
                        # Example of setting equalizer band gain and frequency
                        # await client.set_equalizer_band_gain(0, 3.0)
                        # await client.set_equalizer_band_frequency(0, 100)
                        await client.set_equalizer_params(user_eq)
                        logger.info("EQ settings applied successfully")
                    else:
                        logger.warning(
                            f"API version {info.api_version} is too old. Minimum required: 1.9"
                        )
                        return False

                except Exception as e:
                    logger.error(f"Error applying EQ settings: {e}")
                    return False

            finally:
                try:
                    await client.disconnect()
                    logger.info("Disconnected from device")
                except Exception as e:
                    logger.warning(f"Error during disconnect: {e}")

            return True

    except ClientConnectorError as e:
        logger.error(f"Connection failed - device not reachable at {host}: {e}")
        return False
    except ServerTimeoutError as e:
        logger.error(f"Connection timed out to {host}: {e}")
        return False
    except ClientError as e:
        logger.error(f"HTTP client error connecting to {host}: {e}")
        return False
    except asyncio.TimeoutError:
        logger.error(f"Operation timed out connecting to {host}")
        return False
    except OSError as e:
        logger.error(f"Network error connecting to {host}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error connecting to {host}: {e}")
        return False


async def main():
    """Main application logic."""
    if len(sys.argv) < 2:
        print("Usage: python -m rew2streammagic.main <path_to_eq_file> [host_ip]")
        print("Default host: 192.168.1.29")
        sys.exit(1)

    eq_file = Path(sys.argv[1])
    host = sys.argv[2] if len(sys.argv) > 2 else "192.168.1.29"

    if not eq_file.exists():
        logger.error(f"File not found: {eq_file}")
        sys.exit(1)

    try:
        # Parse EQ file
        logger.info(f"Parsing EQ file: {eq_file}")
        user_eq = parse_eq_file(eq_file)

        if not user_eq.bands:
            logger.error("No equalizer bands found in the file.")
            sys.exit(1)

        # Display parsed bands
        print("First 7 Equalizer Bands:")
        for band in user_eq.bands:
            print(
                f"Band {band.index + 1}: Freq={band.freq}Hz, Gain={band.gain}dB, Q={band.q}"
            )

        # Connect and apply EQ
        success = await connect_and_apply_eq(host, user_eq)

        if success:
            print(f"✅ EQ settings successfully applied to device at {host}")
            return 0
        else:
            print(f"❌ Failed to apply EQ settings to device at {host}")
            return 1

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        return 1


def cli():
    """Command line interface for the script."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
