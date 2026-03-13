


import sys
import zlib
import struct
from twofish import Twofish



BLOCK_SIZE = 16

def xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))

def pad_to_block(data):
    
    if len(data) % BLOCK_SIZE == 0 and len(data) > 0:
        return data
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + b'\x80' + b'\x00' * (pad_len - 1)

def shift_left(block):
    
    result = bytearray(len(block))
    overflow = 0
    for i in range(len(block) - 1, -1, -1):
        result[i] = ((block[i] << 1) | overflow) & 0xFF
        overflow = (block[i] >> 7) & 1
    return bytes(result)

def cmac_subkeys(cipher):
    
    L = cipher.encrypt(b'\x00' * BLOCK_SIZE)
    const_Rb = b'\x00' * 15 + b'\x87'
    
    K1 = shift_left(L)
    if L[0] & 0x80:
        K1 = xor_bytes(K1, const_Rb)
    
    K2 = shift_left(K1)
    if K1[0] & 0x80:
        K2 = xor_bytes(K2, const_Rb)
    
    return K1, K2

def cmac(cipher, message):
    
    K1, K2 = cmac_subkeys(cipher)
    
    n = (len(message) + BLOCK_SIZE - 1) // BLOCK_SIZE
    if n == 0:
        n = 1
    
    
    if len(message) > 0 and len(message) % BLOCK_SIZE == 0:
        
        last_block = xor_bytes(message[-BLOCK_SIZE:], K1)
        prev_blocks = message[:-BLOCK_SIZE]
    else:
        
        remainder = message[-(len(message) % BLOCK_SIZE):] if len(message) % BLOCK_SIZE > 0 else b''
        padded = remainder + b'\x80' + b'\x00' * (BLOCK_SIZE - 1 - len(remainder))
        last_block = xor_bytes(padded, K2)
        prev_blocks = message[:max(0, len(message) - (len(message) % BLOCK_SIZE if len(message) % BLOCK_SIZE > 0 else BLOCK_SIZE))]
    
    X = b'\x00' * BLOCK_SIZE
    
    for i in range(0, len(prev_blocks), BLOCK_SIZE):
        block = prev_blocks[i:i+BLOCK_SIZE]
        X = cipher.encrypt(xor_bytes(X, block))
    
    
    X = cipher.encrypt(xor_bytes(X, last_block))
    return X

def omac_t(cipher, t_value, data):
    
    
    tweak = b'\x00' * (BLOCK_SIZE - 1) + bytes([t_value])
    return cmac(cipher, tweak + data)

def ctr_encrypt(cipher, nonce_mac, data):
    
    counter = bytearray(nonce_mac)
    result = bytearray()
    
    for i in range(0, len(data), BLOCK_SIZE):
        block = data[i:i+BLOCK_SIZE]
        keystream = cipher.encrypt(bytes(counter))
        result.extend(xor_bytes(block, keystream[:len(block)]))
        
        
        carry = 1
        for j in range(BLOCK_SIZE - 1, -1, -1):
            val = counter[j] + carry
            counter[j] = val & 0xFF
            carry = val >> 8
            if carry == 0:
                break
    
    return bytes(result)

def eax_decrypt(key, iv, ciphertext_with_tag, tag_size=16):
    
    cipher = Twofish(key)
    
    
    ciphertext = ciphertext_with_tag[:-tag_size]
    tag = ciphertext_with_tag[-tag_size:]
    
    
    N = omac_t(cipher, 0, iv)
    H = omac_t(cipher, 1, b'')
    
    
    plaintext = ctr_encrypt(cipher, N, ciphertext)
    
    
    C = omac_t(cipher, 2, ciphertext)
    
    
    computed_tag = xor_bytes(xor_bytes(N, C), H)
    if computed_tag != tag:
        raise ValueError(f"EAX authentication failed! Computed tag {computed_tag.hex()} != expected {tag.hex()}")
    
    return plaintext

def eax_encrypt(key, iv, plaintext, tag_size=16):
    
    cipher = Twofish(key)
    
    
    N = omac_t(cipher, 0, iv)
    H = omac_t(cipher, 1, b'')
    
    
    ciphertext = ctr_encrypt(cipher, N, plaintext)
    
    
    C = omac_t(cipher, 2, ciphertext)
    
    
    tag = xor_bytes(xor_bytes(N, C), H)
    
    return ciphertext + tag[:tag_size]




PKA_KEY = bytes([137] * 16)
PKA_IV = bytes([16] * 16)

def deobfuscate_stage1(data):
    
    length = len(data)
    result = bytearray(length)
    for i in range(length):
        idx = length - i - 1  
        val = (length - i * length) & 0xFF
        result[i] = (data[idx] ^ val) & 0xFF
    return bytes(result)

def deobfuscate_stage3(data):
    
    length = len(data)
    result = bytearray(length)
    for i in range(length):
        result[i] = (data[i] ^ ((length - i) & 0xFF)) & 0xFF
    return bytes(result)

def obfuscate_stage2(data):
    
    length = len(data)
    result = bytearray(length)
    for i in range(length):
        result[i] = (data[i] ^ ((length - i) & 0xFF)) & 0xFF
    return bytes(result)

def obfuscate_stage4(data):
    
    length = len(data)
    result = bytearray(length)
    for i in range(length):
        idx = length - i - 1  
        val = (length - i * length) & 0xFF
        result[idx] = (data[i] ^ val) & 0xFF
    return bytes(result)

def qt_uncompress(data):
    
    if len(data) < 4:
        raise ValueError("Data too short for qt uncompress")
    expected_size = struct.unpack('>I', data[:4])[0]
    return zlib.decompress(data[4:])

def qt_compress(data):
    
    compressed = zlib.compress(data)
    header = struct.pack('>I', len(data))
    return header + compressed

def decrypt_pkt(data):
    
    
    stage1 = deobfuscate_stage1(data)
    
    
    stage2 = eax_decrypt(PKA_KEY, PKA_IV, stage1)
    
    
    stage3 = deobfuscate_stage3(stage2)
    
    
    xml = qt_uncompress(stage3)
    
    return xml

def encrypt_pkt(xml):
    
    
    compressed = qt_compress(xml)
    
    
    stage2 = obfuscate_stage2(compressed)
    
    
    stage3 = eax_encrypt(PKA_KEY, PKA_IV, stage2)
    
    
    stage4 = obfuscate_stage4(stage3)
    
    return stage4

def is_old_pt(data):
    
    length = len(data)
    if length <= 5:
        return False
    return ((data[4] ^ ((length - 4) & 0xFF)) & 0xFF == 0x78 or
            (data[5] ^ ((length - 5) & 0xFF)) & 0xFF == 0x9C)

def decrypt_old(data):
    
    result = bytearray(len(data))
    for i in range(len(data)):
        result[i] = (data[i] ^ ((len(data) - i) & 0xFF)) & 0xFF
    return qt_uncompress(bytes(result))

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: pkt_tool.py -d input.pkt output.xml   (decrypt)")
        print("       pkt_tool.py -e input.xml output.pkt   (encrypt)")
        sys.exit(1)
    
    mode = sys.argv[1]
    infile = sys.argv[2]
    outfile = sys.argv[3]
    
    if mode == '-d':
        with open(infile, 'rb') as f:
            data = f.read()
        
        print(f"[*] Opening PKT file '{infile}'")
        print(f"[*] Compressed size: {len(data)} bytes")
        
        if is_old_pt(data):
            print("[*] Detected old PT format")
            xml = decrypt_old(data)
        else:
            print("[*] Detected new PT format (Twofish EAX)")
            xml = decrypt_pkt(data)
        
        print(f"[*] Decompressed size: {len(xml)} bytes")
        
        with open(outfile, 'wb') as f:
            f.write(xml)
        print(f"[*] Written XML to '{outfile}'")
        
    elif mode == '-e':
        with open(infile, 'rb') as f:
            xml = f.read()
        
        print(f"[*] Opening XML file '{infile}'")
        print(f"[*] Uncompressed size: {len(xml)} bytes")
        
        data = encrypt_pkt(xml)
        
        print(f"[*] Compressed+encrypted size: {len(data)} bytes")
        
        with open(outfile, 'wb') as f:
            f.write(data)
        print(f"[*] Written PKT to '{outfile}'")
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
