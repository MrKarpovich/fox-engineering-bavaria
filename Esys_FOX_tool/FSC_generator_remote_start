from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


BODY_LEN = 0x3C
SIGNATURE_LEN = 0x80
VIN_OFFSET = 0x1A
VIN_LEN = 7
APPID_OFFSET = 0x02
DEFAULT_APPID = 0x017C
ALL_APPIDS = (
    0x01A4, 0x01AB, 0x01AC, 0x01AF, 0x01C1, 0x01DE, 0x01E2,
    0x01E3, 0x01E4, 0x01E8, 0x01EC, 0x01EE, 0x01EF, 0x01F0,
    0x01F1, 0x01F2, 0x007B, 0x017C, 0x0095, 0x0180, 0x0188,
)
E = 3

N_RAW_LE = bytes.fromhex(
    """
    03 F8 69 D6 55 B1 80 74 21 3D A6 2C AD C6 17 EC
    BB 84 C1 71 EC B8 13 97 3E 1F 34 D8 4B 9B 18 8E
    1F F2 59 AF 0F 80 EC 3B BD 43 DF B1 90 E2 6F AC
    38 97 59 3C E1 57 10 67 54 A4 29 1B D0 3B C9 7D
    11 A6 9D D7 38 97 CE 1D D3 54 5E A6 2A 2A F5 1A
    AB DA DD 75 0A AB 69 57 CE 41 B0 E5 07 69 F3 F3
    9C 84 36 3F 57 4C EA 92 78 C2 35 64 5B 07 72 80
    79 10 53 6D 5C F9 8C F7 1F 3B EF 8C D4 90 70 F5
    """
)
N = int.from_bytes(N_RAW_LE, "little")

TEMPLATE_BODY = bytes.fromhex(
    """
    01 01 01 7C 00 01 20 20 37 37 33 34 38 37 01 20
    30 30 30 30 30 30 30 1D 61 01 39 4A 32 39 34 33
    36 01 00 00 00 00 00 00 00 00 00 04 02 32 30
    32 36 30 31 30 31 31 30 30 30 5A 00
    """
)

KNOWN_SUFFIX_ONLY_SIGNATURE = bytes.fromhex(
    """
    16 DC 66 62 4B 4D 8C 57 94 0C 5F 9D 13 70 5F 08
    BE A5 C5 19 88 AA D3 3C 3C CF 6C CF D0 07 0C A1
    33 26 D3 1A D0 C2 6A 0E 44 0D C1
    """
)
BUILTIN_TEMPLATE = (
    TEMPLATE_BODY

    + b"\x00"
    + b"\x00" * (SIGNATURE_LEN - len(KNOWN_SUFFIX_ONLY_SIGNATURE))
    + KNOWN_SUFFIX_ONLY_SIGNATURE
)

MD5_DIGEST_INFO_PREFIX = bytes.fromhex(
    "30 20 30 0C 06 08 2A 86 48 86 F7 0D 02 05 05 00 04 10"
)


def floor_cuberoot(value: int) -> int:
    if value < 0:
        raise ValueError("cube root input must be non-negative")
    lo, hi = 0, 1 << ((value.bit_length() + 2) // 3)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid * mid * mid <= value:
            lo = mid
        else:
            hi = mid - 1
    return lo


def ceil_cuberoot(value: int) -> int:
    root = floor_cuberoot(value)
    return root if root * root * root == value else root + 1


def odd_cube_root_mod_2_128(value: int) -> int:
    modulus = 1 << 128
    value %= modulus
    if not value & 1:
        raise ValueError("value must be odd")
    inverse_of_three = pow(3, -1, 1 << 126)
    root = pow(value, inverse_of_three, modulus)
    if pow(root, 3, modulus) != value:
        raise AssertionError("internal modular cube-root failure")
    return root


def forge_suffix_only_signature(digest: bytes) -> tuple[bytes, int, bytes]:

    if len(digest) != 16:
        raise ValueError("MD5 digest must be 16 bytes")

    modulus_128 = 1 << 128
    digest_int = int.from_bytes(digest, "big")

    for quotient in range(256):
        target_low = (digest_int + quotient * N) % modulus_128
        if not target_low & 1:
            continue

        residue = odd_cube_root_mod_2_128(target_low)
        lower = ceil_cuberoot(quotient * N)
        upper = floor_cuberoot((quotient + 1) * N - 1)

        if residue > upper:
            continue
        lift = (upper - residue) // modulus_128
        candidate = residue + lift * modulus_128
        if candidate < lower:
            continue
        if candidate >= N:
            continue

        recovered_int = pow(candidate, E, N)
        recovered = recovered_int.to_bytes(SIGNATURE_LEN, "big")
        if recovered[-16:] != digest:
            continue

        signature = candidate.to_bytes(SIGNATURE_LEN, "big")
        return signature, quotient, recovered

    raise RuntimeError("could not construct a suffix-only signature")


def strict_pkcs1_v1_5_block(digest: bytes) -> bytes:
    digest_info = MD5_DIGEST_INFO_PREFIX + digest
    padding_len = SIGNATURE_LEN - len(digest_info) - 3
    if padding_len < 8:
        raise ValueError("RSA modulus is too short for DigestInfo")
    return b"\x00\x01" + b"\xff" * padding_len + b"\x00" + digest_info


def spaced_hex(data: bytes) -> str:
    return data.hex(" ").upper()


def parse_appid(value: str) -> int:
    text = value.strip()
    try:
        if text.lower().startswith("0x"):
            appid = int(text, 16)
        else:
            appid = int(text, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "App ID must be a hexadecimal value such as 017C or 0x017C"
        ) from exc
    if not 0 <= appid <= 0xFFFF:
        raise argparse.ArgumentTypeError("App ID must fit in 16 bits")
    return appid


def load_template(path: Path | None) -> bytearray:
    data = BUILTIN_TEMPLATE if path is None else path.read_bytes()
    expected = BODY_LEN + SIGNATURE_LEN
    if len(data) < expected:
        raise ValueError(
            f"template is {len(data)} bytes; need at least {expected} bytes"
        )

    return bytearray(data[:BODY_LEN] + data[-SIGNATURE_LEN:])


def build_fsc(
    template: bytearray, vin: bytes, appid: int
) -> tuple[bytes, bytes, int, bytes, bool]:
    output = bytearray(template)
    output[APPID_OFFSET : APPID_OFFSET + 2] = appid.to_bytes(2, "big")
    output[VIN_OFFSET : VIN_OFFSET + VIN_LEN] = vin

    digest = hashlib.md5(output[:BODY_LEN]).digest()
    signature, quotient, recovered = forge_suffix_only_signature(digest)
    output[-SIGNATURE_LEN:] = signature

    stored_signature = int.from_bytes(output[-SIGNATURE_LEN:], "big")
    checked = pow(stored_signature, E, N).to_bytes(SIGNATURE_LEN, "big")
    weak_valid = checked[-16:] == hashlib.md5(output[:BODY_LEN]).digest()
    strict_valid = checked == strict_pkcs1_v1_5_block(digest)
    if not weak_valid or checked != recovered:
        raise AssertionError("generated FSC failed the vulnerable-verifier self-check")

    return bytes(output), digest, quotient, checked, strict_valid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vin7", help="exactly seven ASCII VIN characters")
    appid_group = parser.add_mutually_exclusive_group()
    appid_group.add_argument(
        "-a", "--appid", type=parse_appid, default=DEFAULT_APPID,
        help="16-bit hexadecimal application ID (default: 017C)",
    )
    appid_group.add_argument(
        "--all", action="store_true",
        help="generate the predefined App ID set in a folder named after VIN7",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("forged_poc.fsc"),
        help="output FSC path (default: forged_poc.fsc)",
    )
    parser.add_argument(
        "-t", "--template", type=Path,
        help="optional binary template; built-in supplied template is the default",
    )
    parser.add_argument(
        "--print-hex", action="store_true", help="print the complete output as hex",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        vin = args.vin7.encode("ascii")
    except UnicodeEncodeError as exc:
        raise SystemExit("VIN must contain ASCII characters only") from exc
    if len(vin) != VIN_LEN:
        raise SystemExit("VIN argument must be exactly seven ASCII characters")
    if not args.vin7.isalnum():
        raise SystemExit("VIN argument must contain ASCII letters and digits only")

    template = load_template(args.template)
    if args.all:
        output_dir = Path(args.vin7)
        output_dir.mkdir(exist_ok=True)
        for appid in ALL_APPIDS:
            output, digest, quotient, checked, strict_valid = build_fsc(
                template, vin, appid
            )
            output_path = output_dir / f"FSC_{args.vin7}_{appid:04x}.fsc"
            output_path.write_bytes(output)
            print(
                f"wrote: {output_path} ({len(output)} bytes, "
                f"MD5 {digest.hex().upper()}, q={quotient})"
            )
            if args.print_hex:
                print(spaced_hex(output))
        print(f"generated {len(ALL_APPIDS)} FSC files in {output_dir}/")
        return 0

    output, digest, quotient, checked, strict_valid = build_fsc(
        template, vin, args.appid
    )
    args.output.write_bytes(output)
    stored_signature = int.from_bytes(output[-SIGNATURE_LEN:], "big")

    print(f"wrote:              {args.output} ({len(output)} bytes)")
    print(f"App ID @ 0x{APPID_OFFSET:02x}:      0x{args.appid:04X}")
    print(f"VIN @ 0x{VIN_OFFSET:02x}:         {vin.decode('ascii')}")
    print(f"MD5(body[0:0x3c]): {spaced_hex(digest)}")
    print(f"RSA quotient q:     {quotient}")
    print(f"signature bits:     {stored_signature.bit_length()}")
    print(f"RSA result prefix:  {spaced_hex(checked[:16])}")
    print(f"RSA result suffix:  {spaced_hex(checked[-16:])}")
    print("weak suffix check:  PASS")
    print(f"strict PKCS#1 v1.5: {'PASS' if strict_valid else 'FAIL'}")
    if args.print_hex:
        print(spaced_hex(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
