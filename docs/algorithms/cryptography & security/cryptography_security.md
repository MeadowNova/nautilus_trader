import os
import sys

from . import rsa_key_generator as rkg

DEFAULT_BLOCK_SIZE = 128
BYTE_SIZE = 256


def get_blocks_from_text(
    message: str, block_size: int = DEFAULT_BLOCK_SIZE
) -> list[int]:
    message_bytes = message.encode("ascii")

    block_ints = []
    for block_start in range(0, len(message_bytes), block_size):
        block_int = 0
        for i in range(block_start, min(block_start + block_size, len(message_bytes))):
            block_int += message_bytes[i] * (BYTE_SIZE ** (i % block_size))
        block_ints.append(block_int)
    return block_ints


def get_text_from_blocks(
    block_ints: list[int], message_length: int, block_size: int = DEFAULT_BLOCK_SIZE
) -> str:
    message: list[str] = []
    for block_int in block_ints:
        block_message: list[str] = []
        for i in range(block_size - 1, -1, -1):
            if len(message) + i < message_length:
                ascii_number = block_int // (BYTE_SIZE**i)
                block_int = block_int % (BYTE_SIZE**i)
                block_message.insert(0, chr(ascii_number))
        message.extend(block_message)
    return "".join(message)


def encrypt_message(
    message: str, key: tuple[int, int], block_size: int = DEFAULT_BLOCK_SIZE
) -> list[int]:
    encrypted_blocks = []
    n, e = key

    for block in get_blocks_from_text(message, block_size):
        encrypted_blocks.append(pow(block, e, n))
    return encrypted_blocks


def decrypt_message(
    encrypted_blocks: list[int],
    message_length: int,
    key: tuple[int, int],
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> str:
    decrypted_blocks = []
    n, d = key
    for block in encrypted_blocks:
        decrypted_blocks.append(pow(block, d, n))
    return get_text_from_blocks(decrypted_blocks, message_length, block_size)


def read_key_file(key_filename: str) -> tuple[int, int, int]:
    with open(key_filename) as fo:
        content = fo.read()
    key_size, n, eor_d = content.split(",")
    return (int(key_size), int(n), int(eor_d))


def encrypt_and_write_to_file(
    message_filename: str,
    key_filename: str,
    message: str,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> str:
    key_size, n, e = read_key_file(key_filename)
    if key_size < block_size * 8:
        sys.exit(
            f"ERROR: Block size is {block_size * 8} bits and key size is {key_size} "
            "bits. The RSA cipher requires the block size to be equal to or greater "
            "than the key size. Either decrease the block size or use different keys."
        )

    encrypted_blocks = [str(i) for i in encrypt_message(message, (n, e), block_size)]

    encrypted_content = ",".join(encrypted_blocks)
    encrypted_content = f"{len(message)}_{block_size}_{encrypted_content}"
    with open(message_filename, "w") as fo:
        fo.write(encrypted_content)
    return encrypted_content


def read_from_file_and_decrypt(message_filename: str, key_filename: str) -> str:
    key_size, n, d = read_key_file(key_filename)
    with open(message_filename) as fo:
        content = fo.read()
    message_length_str, block_size_str, encrypted_message = content.split("_")
    message_length = int(message_length_str)
    block_size = int(block_size_str)

    if key_size < block_size * 8:
        sys.exit(
            f"ERROR: Block size is {block_size * 8} bits and key size is {key_size} "
            "bits. The RSA cipher requires the block size to be equal to or greater "
            "than the key size. Were the correct key file and encrypted file specified?"
        )

    encrypted_blocks = []
    for block in encrypted_message.split(","):
        encrypted_blocks.append(int(block))

    return decrypt_message(encrypted_blocks, message_length, (n, d), block_size)


def main() -> None:
    filename = "encrypted_file.txt"
    response = input(r"Encrypt\Decrypt [e\d]: ")

    if response.lower().startswith("e"):
        mode = "encrypt"
    elif response.lower().startswith("d"):
        mode = "decrypt"

    if mode == "encrypt":
        if not os.path.exists("rsa_pubkey.txt"):
            rkg.make_key_files("rsa", 1024)

        message = input("\nEnter message: ")
        pubkey_filename = "rsa_pubkey.txt"
        print(f"Encrypting and writing to {filename}...")
        encrypted_text = encrypt_and_write_to_file(filename, pubkey_filename, message)

        print("\nEncrypted text:")
        print(encrypted_text)

    elif mode == "decrypt":
        privkey_filename = "rsa_privkey.txt"
        print(f"Reading from {filename} and decrypting...")
        decrypted_text = read_from_file_and_decrypt(filename, privkey_filename)
        print("writing decryption to rsa_decryption.txt...")
        with open("rsa_decryption.txt", "w") as dec:
            dec.write(decrypted_text)

        print("\nDecryption:")
        print(decrypted_text)


if __name__ == "__main__":
    main()

============================

from binascii import hexlify
from hashlib import sha256
from os import urandom

# RFC 3526 - More Modular Exponential (MODP) Diffie-Hellman groups for
# Internet Key Exchange (IKE) https://tools.ietf.org/html/rfc3526

primes = {
    # 1536-bit
    5: {
        "prime": int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF",
            base=16,
        ),
        "generator": 2,
    },
    # 2048-bit
    14: {
        "prime": int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
            "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
            "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
            "15728E5A8AACAA68FFFFFFFFFFFFFFFF",
            base=16,
        ),
        "generator": 2,
    },
    # 3072-bit
    15: {
        "prime": int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
            "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
            "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
            "15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64"
            "ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
            "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B"
            "F12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
            "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31"
            "43DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF",
            base=16,
        ),
        "generator": 2,
    },
    # 4096-bit
    16: {
        "prime": int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
            "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
            "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
            "15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64"
            "ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
            "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B"
            "F12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
            "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31"
            "43DB5BFCE0FD108E4B82D120A92108011A723C12A787E6D7"
            "88719A10BDBA5B2699C327186AF4E23C1A946834B6150BDA"
            "2583E9CA2AD44CE8DBBBC2DB04DE8EF92E8EFC141FBECAA6"
            "287C59474E6BC05D99B2964FA090C3A2233BA186515BE7ED"
            "1F612970CEE2D7AFB81BDD762170481CD0069127D5B05AA9"
            "93B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934063199"
            "FFFFFFFFFFFFFFFF",
            base=16,
        ),
        "generator": 2,
    },
    # 6144-bit
    17: {
        "prime": int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E08"
            "8A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B"
            "302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9"
            "A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE6"
            "49286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8"
            "FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C"
            "180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
            "3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D"
            "04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7D"
            "B3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D226"
            "1AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
            "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFC"
            "E0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B26"
            "99C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB"
            "04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2"
            "233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127"
            "D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934028492"
            "36C3FAB4D27C7026C1D4DCB2602646DEC9751E763DBA37BDF8FF9406"
            "AD9E530EE5DB382F413001AEB06A53ED9027D831179727B0865A8918"
            "DA3EDBEBCF9B14ED44CE6CBACED4BB1BDB7F1447E6CC254B33205151"
            "2BD7AF426FB8F401378CD2BF5983CA01C64B92ECF032EA15D1721D03"
            "F482D7CE6E74FEF6D55E702F46980C82B5A84031900B1C9E59E7C97F"
            "BEC7E8F323A97A7E36CC88BE0F1D45B7FF585AC54BD407B22B4154AA"
            "CC8F6D7EBF48E1D814CC5ED20F8037E0A79715EEF29BE32806A1D58B"
            "B7C5DA76F550AA3D8A1FBFF0EB19CCB1A313D55CDA56C9EC2EF29632"
            "387FE8D76E3C0468043E8F663F4860EE12BF2D5B0B7474D6E694F91E"
            "6DCC4024FFFFFFFFFFFFFFFF",
            base=16,
        ),
        "generator": 2,
    },
    # 8192-bit
    18: {
        "prime": int(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
            "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
            "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
            "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
            "15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64"
            "ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
            "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B"
            "F12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
            "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31"
            "43DB5BFCE0FD108E4B82D120A92108011A723C12A787E6D7"
            "88719A10BDBA5B2699C327186AF4E23C1A946834B6150BDA"
            "2583E9CA2AD44CE8DBBBC2DB04DE8EF92E8EFC141FBECAA6"
            "287C59474E6BC05D99B2964FA090C3A2233BA186515BE7ED"
            "1F612970CEE2D7AFB81BDD762170481CD0069127D5B05AA9"
            "93B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934028492"
            "36C3FAB4D27C7026C1D4DCB2602646DEC9751E763DBA37BD"
            "F8FF9406AD9E530EE5DB382F413001AEB06A53ED9027D831"
            "179727B0865A8918DA3EDBEBCF9B14ED44CE6CBACED4BB1B"
            "DB7F1447E6CC254B332051512BD7AF426FB8F401378CD2BF"
            "5983CA01C64B92ECF032EA15D1721D03F482D7CE6E74FEF6"
            "D55E702F46980C82B5A84031900B1C9E59E7C97FBEC7E8F3"
            "23A97A7E36CC88BE0F1D45B7FF585AC54BD407B22B4154AA"
            "CC8F6D7EBF48E1D814CC5ED20F8037E0A79715EEF29BE328"
            "06A1D58BB7C5DA76F550AA3D8A1FBFF0EB19CCB1A313D55C"
            "DA56C9EC2EF29632387FE8D76E3C0468043E8F663F4860EE"
            "12BF2D5B0B7474D6E694F91E6DBE115974A3926F12FEE5E4"
            "38777CB6A932DF8CD8BEC4D073B931BA3BC832B68D9DD300"
            "741FA7BF8AFC47ED2576F6936BA424663AAB639C5AE4F568"
            "3423B4742BF1C978238F16CBE39D652DE3FDB8BEFC848AD9"
            "22222E04A4037C0713EB57A81A23F0C73473FC646CEA306B"
            "4BCBC8862F8385DDFA9D4B7FA2C087E879683303ED5BDD3A"
            "062B3CF5B3A278A66D2A13F83F44F82DDF310EE074AB6A36"
            "4597E899A0255DC164F31CC50846851DF9AB48195DED7EA1"
            "B1D510BD7EE74D73FAF36BC31ECFA268359046F4EB879F92"
            "4009438B481C6CD7889A002ED5EE382BC9190DA6FC026E47"
            "9558E4475677E9AA9E3050E2765694DFC81F56E880B96E71"
            "60C980DD98EDD3DFFFFFFFFFFFFFFFFF",
            base=16,
        ),
        "generator": 2,
    },
}


class DiffieHellman:
    """
    Class to represent the Diffie-Hellman key exchange protocol


    >>> alice = DiffieHellman()
    >>> bob = DiffieHellman()

    >>> alice_private = alice.get_private_key()
    >>> alice_public = alice.generate_public_key()

    >>> bob_private = bob.get_private_key()
    >>> bob_public = bob.generate_public_key()

    >>> # generating shared key using the DH object
    >>> alice_shared = alice.generate_shared_key(bob_public)
    >>> bob_shared = bob.generate_shared_key(alice_public)

    >>> assert alice_shared == bob_shared

    >>> # generating shared key using static methods
    >>> alice_shared = DiffieHellman.generate_shared_key_static(
    ...     alice_private, bob_public
    ... )
    >>> bob_shared = DiffieHellman.generate_shared_key_static(
    ...     bob_private, alice_public
    ... )

    >>> assert alice_shared == bob_shared
    """

    # Current minimum recommendation is 2048 bit (group 14)
    def __init__(self, group: int = 14) -> None:
        if group not in primes:
            raise ValueError("Unsupported Group")
        self.prime = primes[group]["prime"]
        self.generator = primes[group]["generator"]

        self.__private_key = int(hexlify(urandom(32)), base=16)

    def get_private_key(self) -> str:
        return hex(self.__private_key)[2:]

    def generate_public_key(self) -> str:
        public_key = pow(self.generator, self.__private_key, self.prime)
        return hex(public_key)[2:]

    def is_valid_public_key(self, key: int) -> bool:
        # check if the other public key is valid based on NIST SP800-56
        return (
            2 <= key <= self.prime - 2
            and pow(key, (self.prime - 1) // 2, self.prime) == 1
        )

    def generate_shared_key(self, other_key_str: str) -> str:
        other_key = int(other_key_str, base=16)
        if not self.is_valid_public_key(other_key):
            raise ValueError("Invalid public key")
        shared_key = pow(other_key, self.__private_key, self.prime)
        return sha256(str(shared_key).encode()).hexdigest()

    @staticmethod
    def is_valid_public_key_static(remote_public_key_str: int, prime: int) -> bool:
        # check if the other public key is valid based on NIST SP800-56
        return (
            2 <= remote_public_key_str <= prime - 2
            and pow(remote_public_key_str, (prime - 1) // 2, prime) == 1
        )

    @staticmethod
    def generate_shared_key_static(
        local_private_key_str: str, remote_public_key_str: str, group: int = 14
    ) -> str:
        local_private_key = int(local_private_key_str, base=16)
        remote_public_key = int(remote_public_key_str, base=16)
        prime = primes[group]["prime"]
        if not DiffieHellman.is_valid_public_key_static(remote_public_key, prime):
            raise ValueError("Invalid public key")
        shared_key = pow(remote_public_key, local_private_key, prime)
        return sha256(str(shared_key).encode()).hexdigest()


if __name__ == "__main__":
    import doctest

    doctest.testmod()

===========================================

# Author: M. Yathurshan
# Black Formatter: True

"""
Implementation of SHA256 Hash function in a Python class and provides utilities
to find hash of string or hash of text from a file.

Usage: python sha256.py --string "Hello World!!"
       python sha256.py --file "hello_world.txt"
       When run without any arguments,
       it prints the hash of the string "Hello World!! Welcome to Cryptography"

References:
https://qvault.io/cryptography/how-sha-2-works-step-by-step-sha-256/
https://en.wikipedia.org/wiki/SHA-2
"""

import argparse
import struct
import unittest


class SHA256:
    """
    Class to contain the entire pipeline for SHA1 Hashing Algorithm

    >>> SHA256(b'Python').hash
    '18885f27b5af9012df19e496460f9294d5ab76128824c6f993787004f6d9a7db'

    >>> SHA256(b'hello world').hash
    'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
    """

    def __init__(self, data: bytes) -> None:
        self.data = data

        # Initialize hash values
        self.hashes = [
            0x6A09E667,
            0xBB67AE85,
            0x3C6EF372,
            0xA54FF53A,
            0x510E527F,
            0x9B05688C,
            0x1F83D9AB,
            0x5BE0CD19,
        ]

        # Initialize round constants
        self.round_constants = [
            0x428A2F98,
            0x71374491,
            0xB5C0FBCF,
            0xE9B5DBA5,
            0x3956C25B,
            0x59F111F1,
            0x923F82A4,
            0xAB1C5ED5,
            0xD807AA98,
            0x12835B01,
            0x243185BE,
            0x550C7DC3,
            0x72BE5D74,
            0x80DEB1FE,
            0x9BDC06A7,
            0xC19BF174,
            0xE49B69C1,
            0xEFBE4786,
            0x0FC19DC6,
            0x240CA1CC,
            0x2DE92C6F,
            0x4A7484AA,
            0x5CB0A9DC,
            0x76F988DA,
            0x983E5152,
            0xA831C66D,
            0xB00327C8,
            0xBF597FC7,
            0xC6E00BF3,
            0xD5A79147,
            0x06CA6351,
            0x14292967,
            0x27B70A85,
            0x2E1B2138,
            0x4D2C6DFC,
            0x53380D13,
            0x650A7354,
            0x766A0ABB,
            0x81C2C92E,
            0x92722C85,
            0xA2BFE8A1,
            0xA81A664B,
            0xC24B8B70,
            0xC76C51A3,
            0xD192E819,
            0xD6990624,
            0xF40E3585,
            0x106AA070,
            0x19A4C116,
            0x1E376C08,
            0x2748774C,
            0x34B0BCB5,
            0x391C0CB3,
            0x4ED8AA4A,
            0x5B9CCA4F,
            0x682E6FF3,
            0x748F82EE,
            0x78A5636F,
            0x84C87814,
            0x8CC70208,
            0x90BEFFFA,
            0xA4506CEB,
            0xBEF9A3F7,
            0xC67178F2,
        ]

        self.preprocessed_data = self.preprocessing(self.data)
        self.final_hash()

    @staticmethod
    def preprocessing(data: bytes) -> bytes:
        padding = b"\x80" + (b"\x00" * (63 - (len(data) + 8) % 64))
        big_endian_integer = struct.pack(">Q", (len(data) * 8))
        return data + padding + big_endian_integer

    def final_hash(self) -> None:
        # Convert into blocks of 64 bytes
        self.blocks = [
            self.preprocessed_data[x : x + 64]
            for x in range(0, len(self.preprocessed_data), 64)
        ]

        for block in self.blocks:
            # Convert the given block into a list of 4 byte integers
            words = list(struct.unpack(">16L", block))
            # add 48 0-ed integers
            words += [0] * 48

            a, b, c, d, e, f, g, h = self.hashes

            for index in range(64):
                if index > 15:
                    # modify the zero-ed indexes at the end of the array
                    s0 = (
                        self.ror(words[index - 15], 7)
                        ^ self.ror(words[index - 15], 18)
                        ^ (words[index - 15] >> 3)
                    )
                    s1 = (
                        self.ror(words[index - 2], 17)
                        ^ self.ror(words[index - 2], 19)
                        ^ (words[index - 2] >> 10)
                    )

                    words[index] = (
                        words[index - 16] + s0 + words[index - 7] + s1
                    ) % 0x100000000

                # Compression
                s1 = self.ror(e, 6) ^ self.ror(e, 11) ^ self.ror(e, 25)
                ch = (e & f) ^ ((~e & (0xFFFFFFFF)) & g)
                temp1 = (
                    h + s1 + ch + self.round_constants[index] + words[index]
                ) % 0x100000000
                s0 = self.ror(a, 2) ^ self.ror(a, 13) ^ self.ror(a, 22)
                maj = (a & b) ^ (a & c) ^ (b & c)
                temp2 = (s0 + maj) % 0x100000000

                h, g, f, e, d, c, b, a = (
                    g,
                    f,
                    e,
                    ((d + temp1) % 0x100000000),
                    c,
                    b,
                    a,
                    ((temp1 + temp2) % 0x100000000),
                )

            mutated_hash_values = [a, b, c, d, e, f, g, h]

            # Modify final values
            self.hashes = [
                ((element + mutated_hash_values[index]) % 0x100000000)
                for index, element in enumerate(self.hashes)
            ]

        self.hash = "".join([hex(value)[2:].zfill(8) for value in self.hashes])

    def ror(self, value: int, rotations: int) -> int:
        """
        Right rotate a given unsigned number by a certain amount of rotations
        """
        return 0xFFFFFFFF & (value << (32 - rotations)) | (value >> rotations)


class SHA256HashTest(unittest.TestCase):
    """
    Test class for the SHA256 class. Inherits the TestCase class from unittest
    """

    def test_match_hashes(self) -> None:
        import hashlib

        msg = bytes("Test String", "utf-8")
        assert SHA256(msg).hash == hashlib.sha256(msg).hexdigest()


def main() -> None:
    """
    Provides option 'string' or 'file' to take input
    and prints the calculated SHA-256 hash
    """

    # unittest.main()

    import doctest

    doctest.testmod()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--string",
        dest="input_string",
        default="Hello World!! Welcome to Cryptography",
        help="Hash the string",
    )
    parser.add_argument(
        "-f", "--file", dest="input_file", help="Hash contents of a file"
    )

    args = parser.parse_args()

    input_string = args.input_string

    # hash input should be a bytestring
    if args.input_file:
        with open(args.input_file, "rb") as f:
            hash_input = f.read()
    else:
        hash_input = bytes(input_string, "utf-8")

    print(SHA256(hash_input).hash)


if __name__ == "__main__":
    main()

===================================

"""
The MD5 algorithm is a hash function that's commonly used as a checksum to
detect data corruption. The algorithm works by processing a given message in
blocks of 512 bits, padding the message as needed. It uses the blocks to operate
a 128-bit state and performs a total of 64 such operations. Note that all values
are little-endian, so inputs are converted as needed.

Although MD5 was used as a cryptographic hash function in the past, it's since
been cracked, so it shouldn't be used for security purposes.

For more info, see https://en.wikipedia.org/wiki/MD5
"""

from collections.abc import Generator
from math import sin


def to_little_endian(string_32: bytes) -> bytes:
    """
    Converts the given string to little-endian in groups of 8 chars.

    Arguments:
        string_32 {[string]} -- [32-char string]

    Raises:
        ValueError -- [input is not 32 char]

    Returns:
        32-char little-endian string
    >>> to_little_endian(b'1234567890abcdfghijklmnopqrstuvw')
    b'pqrstuvwhijklmno90abcdfg12345678'
    >>> to_little_endian(b'1234567890')
    Traceback (most recent call last):
    ...
    ValueError: Input must be of length 32
    """
    if len(string_32) != 32:
        raise ValueError("Input must be of length 32")

    little_endian = b""
    for i in [3, 2, 1, 0]:
        little_endian += string_32[8 * i : 8 * i + 8]
    return little_endian


def reformat_hex(i: int) -> bytes:
    """
    Converts the given non-negative integer to hex string.

    Example: Suppose the input is the following:
        i = 1234

        The input is 0x000004d2 in hex, so the little-endian hex string is
        "d2040000".

    Arguments:
        i {[int]} -- [integer]

    Raises:
        ValueError -- [input is negative]

    Returns:
        8-char little-endian hex string

    >>> reformat_hex(1234)
    b'd2040000'
    >>> reformat_hex(666)
    b'9a020000'
    >>> reformat_hex(0)
    b'00000000'
    >>> reformat_hex(1234567890)
    b'd2029649'
    >>> reformat_hex(1234567890987654321)
    b'b11c6cb1'
    >>> reformat_hex(-1)
    Traceback (most recent call last):
    ...
    ValueError: Input must be non-negative
    """
    if i < 0:
        raise ValueError("Input must be non-negative")

    hex_rep = format(i, "08x")[-8:]
    little_endian_hex = b""
    for j in [3, 2, 1, 0]:
        little_endian_hex += hex_rep[2 * j : 2 * j + 2].encode("utf-8")
    return little_endian_hex


def preprocess(message: bytes) -> bytes:
    """
    Preprocesses the message string:
    - Convert message to bit string
    - Pad bit string to a multiple of 512 chars:
        - Append a 1
        - Append 0's until length = 448 (mod 512)
        - Append length of original message (64 chars)

    Example: Suppose the input is the following:
        message = "a"

        The message bit string is "01100001", which is 8 bits long. Thus, the
        bit string needs 439 bits of padding so that
        (bit_string + "1" + padding) = 448 (mod 512).
        The message length is "000010000...0" in 64-bit little-endian binary.
        The combined bit string is then 512 bits long.

    Arguments:
        message {[string]} -- [message string]

    Returns:
        processed bit string padded to a multiple of 512 chars

    >>> preprocess(b"a") == (b"01100001" + b"1" +
    ...                     (b"0" * 439) + b"00001000" + (b"0" * 56))
    True
    >>> preprocess(b"") == b"1" + (b"0" * 447) + (b"0" * 64)
    True
    """
    bit_string = b""
    for char in message:
        bit_string += format(char, "08b").encode("utf-8")
    start_len = format(len(bit_string), "064b").encode("utf-8")

    # Pad bit_string to a multiple of 512 chars
    bit_string += b"1"
    while len(bit_string) % 512 != 448:
        bit_string += b"0"
    bit_string += to_little_endian(start_len[32:]) + to_little_endian(start_len[:32])

    return bit_string


def get_block_words(bit_string: bytes) -> Generator[list[int]]:
    """
    Splits bit string into blocks of 512 chars and yields each block as a list
    of 32-bit words

    Example: Suppose the input is the following:
        bit_string =
            "000000000...0" +  # 0x00 (32 bits, padded to the right)
            "000000010...0" +  # 0x01 (32 bits, padded to the right)
            "000000100...0" +  # 0x02 (32 bits, padded to the right)
            "000000110...0" +  # 0x03 (32 bits, padded to the right)
            ...
            "000011110...0"    # 0x0a (32 bits, padded to the right)

        Then len(bit_string) == 512, so there'll be 1 block. The block is split
        into 32-bit words, and each word is converted to little endian. The
        first word is interpreted as 0 in decimal, the second word is
        interpreted as 1 in decimal, etc.

        Thus, block_words == [[0, 1, 2, 3, ..., 15]].

    Arguments:
        bit_string {[string]} -- [bit string with multiple of 512 as length]

    Raises:
        ValueError -- [length of bit string isn't multiple of 512]

    Yields:
        a list of 16 32-bit words

    >>> test_string = ("".join(format(n << 24, "032b") for n in range(16))
    ...                  .encode("utf-8"))
    >>> list(get_block_words(test_string))
    [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]]
    >>> list(get_block_words(test_string * 4)) == [list(range(16))] * 4
    True
    >>> list(get_block_words(b"1" * 512)) == [[4294967295] * 16]
    True
    >>> list(get_block_words(b""))
    []
    >>> list(get_block_words(b"1111"))
    Traceback (most recent call last):
    ...
    ValueError: Input must have length that's a multiple of 512
    """
    if len(bit_string) % 512 != 0:
        raise ValueError("Input must have length that's a multiple of 512")

    for pos in range(0, len(bit_string), 512):
        block = bit_string[pos : pos + 512]
        block_words = []
        for i in range(0, 512, 32):
            block_words.append(int(to_little_endian(block[i : i + 32]), 2))
        yield block_words


def not_32(i: int) -> int:
    """
    Perform bitwise NOT on given int.

    Arguments:
        i {[int]} -- [given int]

    Raises:
        ValueError -- [input is negative]

    Returns:
        Result of bitwise NOT on i

    >>> not_32(34)
    4294967261
    >>> not_32(1234)
    4294966061
    >>> not_32(4294966061)
    1234
    >>> not_32(0)
    4294967295
    >>> not_32(1)
    4294967294
    >>> not_32(-1)
    Traceback (most recent call last):
    ...
    ValueError: Input must be non-negative
    """
    if i < 0:
        raise ValueError("Input must be non-negative")

    i_str = format(i, "032b")
    new_str = ""
    for c in i_str:
        new_str += "1" if c == "0" else "0"
    return int(new_str, 2)


def sum_32(a: int, b: int) -> int:
    """
    Add two numbers as 32-bit ints.

    Arguments:
        a {[int]} -- [first given int]
        b {[int]} -- [second given int]

    Returns:
        (a + b) as an unsigned 32-bit int

    >>> sum_32(1, 1)
    2
    >>> sum_32(2, 3)
    5
    >>> sum_32(0, 0)
    0
    >>> sum_32(-1, -1)
    4294967294
    >>> sum_32(4294967295, 1)
    0
    """
    return (a + b) % 2**32


def left_rotate_32(i: int, shift: int) -> int:
    """
    Rotate the bits of a given int left by a given amount.

    Arguments:
        i {[int]} -- [given int]
        shift {[int]} -- [shift amount]

    Raises:
        ValueError -- [either given int or shift is negative]

    Returns:
        `i` rotated to the left by `shift` bits

    >>> left_rotate_32(1234, 1)
    2468
    >>> left_rotate_32(1111, 4)
    17776
    >>> left_rotate_32(2147483648, 1)
    1
    >>> left_rotate_32(2147483648, 3)
    4
    >>> left_rotate_32(4294967295, 4)
    4294967295
    >>> left_rotate_32(1234, 0)
    1234
    >>> left_rotate_32(0, 0)
    0
    >>> left_rotate_32(-1, 0)
    Traceback (most recent call last):
    ...
    ValueError: Input must be non-negative
    >>> left_rotate_32(0, -1)
    Traceback (most recent call last):
    ...
    ValueError: Shift must be non-negative
    """
    if i < 0:
        raise ValueError("Input must be non-negative")
    if shift < 0:
        raise ValueError("Shift must be non-negative")
    return ((i << shift) ^ (i >> (32 - shift))) % 2**32


def md5_me(message: bytes) -> bytes:
    """
    Returns the 32-char MD5 hash of a given message.

    Reference: https://en.wikipedia.org/wiki/MD5#Algorithm

    Arguments:
        message {[string]} -- [message]

    Returns:
        32-char MD5 hash string

    >>> md5_me(b"")
    b'd41d8cd98f00b204e9800998ecf8427e'
    >>> md5_me(b"The quick brown fox jumps over the lazy dog")
    b'9e107d9d372bb6826bd81d3542a419d6'
    >>> md5_me(b"The quick brown fox jumps over the lazy dog.")
    b'e4d909c290d0fb1ca068ffaddf22cbd0'

    >>> import hashlib
    >>> from string import ascii_letters
    >>> msgs = [b"", ascii_letters.encode("utf-8"), "Üñîçø∂é".encode("utf-8"),
    ...         b"The quick brown fox jumps over the lazy dog."]
    >>> all(md5_me(msg) == hashlib.md5(msg).hexdigest().encode("utf-8") for msg in msgs)
    True
    """

    # Convert to bit string, add padding and append message length
    bit_string = preprocess(message)

    added_consts = [int(2**32 * abs(sin(i + 1))) for i in range(64)]

    # Starting states
    a0 = 0x67452301
    b0 = 0xEFCDAB89
    c0 = 0x98BADCFE
    d0 = 0x10325476

    shift_amounts = [
        7,
        12,
        17,
        22,
        7,
        12,
        17,
        22,
        7,
        12,
        17,
        22,
        7,
        12,
        17,
        22,
        5,
        9,
        14,
        20,
        5,
        9,
        14,
        20,
        5,
        9,
        14,
        20,
        5,
        9,
        14,
        20,
        4,
        11,
        16,
        23,
        4,
        11,
        16,
        23,
        4,
        11,
        16,
        23,
        4,
        11,
        16,
        23,
        6,
        10,
        15,
        21,
        6,
        10,
        15,
        21,
        6,
        10,
        15,
        21,
        6,
        10,
        15,
        21,
    ]

    # Process bit string in chunks, each with 16 32-char words
    for block_words in get_block_words(bit_string):
        a = a0
        b = b0
        c = c0
        d = d0

        # Hash current chunk
        for i in range(64):
            if i <= 15:
                # f = (b & c) | (not_32(b) & d)     # Alternate definition for f
                f = d ^ (b & (c ^ d))
                g = i
            elif i <= 31:
                # f = (d & b) | (not_32(d) & c)     # Alternate definition for f
                f = c ^ (d & (b ^ c))
                g = (5 * i + 1) % 16
            elif i <= 47:
                f = b ^ c ^ d
                g = (3 * i + 5) % 16
            else:
                f = c ^ (b | not_32(d))
                g = (7 * i) % 16
            f = (f + a + added_consts[i] + block_words[g]) % 2**32
            a = d
            d = c
            c = b
            b = sum_32(b, left_rotate_32(f, shift_amounts[i]))

        # Add hashed chunk to running total
        a0 = sum_32(a0, a)
        b0 = sum_32(b0, b)
        c0 = sum_32(c0, c)
        d0 = sum_32(d0, d)

    digest = reformat_hex(a0) + reformat_hex(b0) + reformat_hex(c0) + reformat_hex(d0)
    return digest


if __name__ == "__main__":
    import doctest

    doctest.testmod()

========================================




