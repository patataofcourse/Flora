import struct

def decompress(data):  # sourcery skip: hoist-if-from-if
    """
    Decompress RLE-compressed data.
    """
    
    if data[0] != 0x30:
        raise TypeError("This isn't an RLE-compressed file.")
    
    dataLen = struct.unpack_from('<I', data)[0] >> 8
    
    out = bytearray(dataLen)
    inPos, outPos = 4, 0
    
    while dataLen > 0:
        if inPos >= len(data):
            raise EOFError("Invalid RLE-compressed file: data stream is too short")
        
        d = data[inPos]; inPos += 1
        
        compressed = (d & 0x80) != 0
        n = d & 0x7f
        
        if compressed:
            if inPos >= len(data):
                raise EOFError("Invalid RLE-compressed file: data stream is too short")
            n+=3
            if dataLen - n < 0:
                raise EOFError("Invalid RLE-compressed file: data stream is too long")
            
            b = data[inPos]; inPos += 1
            for _ in range(n):
                out[outPos] = b
                outPos += 1; dataLen -= 1
        else:
            if inPos + n >= len(data):
                raise EOFError("Invalid RLE-compressed file: data stream is too short")
            n+=1
            if dataLen - n < 0:
                raise EOFError("Invalid RLE-compressed file: data stream is too long")
            
            for _ in range(n):
                out[outPos] = data[inPos]
                outPos += 1; inPos += 1; dataLen -= 1
    
    if inPos < len(data):
        # the input may be 4-byte aligned
        inPos = inPos - (inPos % 4) + (4 if inPos % 4 != 0 else 0)
        if inPos < len(data):
            raise EOFError("Invalid RLE-compressed file: data stream is too long")
    
    return bytes(out)