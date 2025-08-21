"""
Main entry point for parsing a Room EQ Wizard (REW) equalizer description file
and extracting the first seven equalizer band settings.
"""

import sys
import re
import asyncio
import ipaddress
import logging
import argparse
from pathlib import Path
from aiohttp import (
    ClientSession,
    ClientConnectorError,
    ClientError,
    ClientTimeout,
)
from aiostreammagic import StreamMagicClient, EQBand, UserEQ, EQFilterType, Info
from packaging.version import Version

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress all logs from libraries that spam tracebacks
logging.getLogger("aiohttp").setLevel(logging.CRITICAL)
logging.getLogger("aiostreammagic").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)


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


async def connect_and_apply_eq(host, user_eq, timeout=5):
    """Connect to StreamMagic device and apply EQ settings."""

    # Validate IP address
    try:
        # This will validate both IPv4 and IPv6 addresses
        host = str(ipaddress.ip_address(host))
    except ValueError as e:
        logger.error(f"Invalid IP address: {host} - {e}")
        return False

    try:
        # Create session with timeout
        timeout_config = ClientTimeout(total=timeout)
        async with ClientSession(timeout=timeout_config) as session:
            logger.info(f"Attempting to connect to {host}")
            client = StreamMagicClient(host, session=session)

            await client.connect()
            logger.info(f"Successfully connected to {host}")

            # Get device info
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

            await client.disconnect()
            logger.info(f"Disconnected from {host}")

            return True

    except (TimeoutError, asyncio.TimeoutError):
        logger.error(f"Connection timed out to {host}")
        return False
    except ClientConnectorError:
        logger.error(f"Connection failed - device not reachable at {host}")
        return False
    except ClientError as e:
        logger.error(f"HTTP client error connecting to {host}: {e}")
        return False
    except OSError as e:
        logger.error(f"Network error connecting to {host}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error connecting to {host}: {e}")
        return False


async def main(eq_file_path, host, timeout=5, dry_run=False):
    """Main application logic."""

    if dry_run:
        print("🔍 DRY RUN: Device connection will be skipped.")

    eq_file = Path(eq_file_path)

    if not eq_file.exists():
        logger.error(f"File not found: {eq_file}")
        return 1

    try:
        # Parse EQ file
        logger.info(f"Parsing EQ file: {eq_file}")
        user_eq = parse_eq_file(eq_file)

        if not user_eq.bands:
            logger.error("No equalizer bands found in the file.")
            return 1

        # Display parsed bands
        print("First 7 Equalizer Bands:")
        for band in user_eq.bands:
            print(
                f"Band {band.index + 1}: Freq={band.freq}Hz, Gain={band.gain}dB, Q={band.q}"
            )

        if dry_run:
            print("🔍 DRY RUN: EQ file parsed successfully.")
            return 0

        # Connect and apply EQ
        success = await connect_and_apply_eq(host, user_eq, timeout)

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
    parser = argparse.ArgumentParser(
        description="Apply Room EQ Wizard settings to Cambridge CXN 100",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m rew2streammagic.main eq_file.txt
  python -m rew2streammagic.main eq_file.txt --host 192.168.1.50
  python -m rew2streammagic.main eq_file.txt --timeout 10 --dry-run
        """,
    )

    parser.add_argument(
        "eq_file", help="Path to Room EQ Wizard equalizer description file"
    )

    parser.add_argument(
        "--host",
        default="192.168.1.29",
        help="IP address of the Cambridge CXN 100 device (default: 192.168.1.29)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Connection timeout in seconds (default: 5)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse EQ file but don't connect to device or apply settings",
    )

    try:
        args = parser.parse_args()
        exit_code = asyncio.run(
            main(args.eq_file, args.host, args.timeout, args.dry_run)
        )
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
