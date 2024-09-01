import struct

def decompress(data):  # sourcery skip: remove-unreachable-code
    """
    Decompress HUFF-compressed data.
    """
    
    block_size = 8
    
    if data[0] == 0x24:
        block_size = 4
    elif data[0] == 0x28:
        block_size = 8
    else:
        raise TypeError("This isn't a HUFF-compressed file.")
    
    dataLen = struct.unpack_from('<I', data)[0] >> 8
    
    treeSize = (data[4] + 1) * 2
    treeEnd = (4+treeSize)
    
    out = bytearray(dataLen)
    inPos, outPos = 5, 0
    
    
    
    raise NotImplementedError("huffman decompression")
    
    return bytes(out)
