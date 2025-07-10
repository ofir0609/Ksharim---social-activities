# Download 'pycrptodome' with pip in via the terminal
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA


def generate_aes_key():
    return get_random_bytes(16)


def aes_encrypt(key, message):
    cipher = AES.new(key, AES.MODE_ECB)
    # Pad the message to be a multiple of 16 bytes (AES block size)
    padded_message = message + (AES.block_size - len(message) % AES.block_size) * b"\0"
    ciphertext = cipher.encrypt(padded_message)
    return ciphertext


def aes_decrypt(key, ciphertext):
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_message = cipher.decrypt(ciphertext)
    # Remove padding from decrypted message
    unpadded_message = decrypted_message.rstrip(b"\0")
    return unpadded_message


def generate_rsa_keys():
    rsa_key = RSA.generate(2048)
    private_key = rsa_key.export_key()
    public_key = rsa_key.public_key().export_key()
    return private_key, public_key


def rsa_encrypt(public_key, message):
    if isinstance(message, str):  # Check if message is a string
        message = message.encode()  # Encode message if it's a string
    #public_key = RSA.import_key(public_key)
    cipher = PKCS1_OAEP.new(public_key)
    encrypted_message = cipher.encrypt(message)
    return encrypted_message


def rsa_decrypt(private_key, encrypted_message):
    private_key = RSA.import_key(private_key)
    cipher = PKCS1_OAEP.new(private_key)
    decrypted_message = cipher.decrypt(encrypted_message)
    try:
        return decrypted_message.decode('utf-8')  # Attempt to decode as UTF-8
    except UnicodeDecodeError:
        return decrypted_message  # Return bytes if decoding fails