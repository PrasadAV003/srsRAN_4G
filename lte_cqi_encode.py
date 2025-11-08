#!/usr/bin/env python3
"""
LTE CQI Encoder - Python Implementation
Based on 3GPP TS 36.212 Sections 5.2.2.6 and 5.2.2.6.4
Compatible with MATLAB lteCQIEncode function interface

References:
- srsRAN_4G: lib/src/phy/phch/uci.c and lib/src/phy/fec/block/block.c
- 3GPP TS 36.212: Multiplexing and channel coding
- MATLAB LTE Toolbox: lteCQIEncode

Copyright 2024
"""

import numpy as np
from typing import Union, List, Dict, Tuple


# ============================================================================
# Table 5.2.2.6.4-1: Basis sequences for (32, O) block code
# From TS 36.212 Section 5.2.2.6.4
# ============================================================================
M_BASIS_SEQ = np.array([
    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],  # M_0
    [1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1],  # M_1
    [1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1],  # M_2
    [1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1],  # M_3
    [1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1],  # M_4
    [1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1],  # M_5
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1],  # M_6
    [1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1],  # M_7
    [1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1],  # M_8
    [1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1],  # M_9
    [1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1],  # M_10
    [1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1],  # M_11
    [1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1],  # M_12
    [1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1],  # M_13
    [1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1],  # M_14
    [1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1],  # M_15
    [1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0],  # M_16
    [1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0],  # M_17
    [1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0],  # M_18
    [1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],  # M_19
    [1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1],  # M_20
    [1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1],  # M_21
    [1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1],  # M_22
    [1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1],  # M_23
    [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0],  # M_24
    [1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1],  # M_25
    [1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0],  # M_26
    [1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0],  # M_27
    [1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0],  # M_28
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0],  # M_29
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # M_30
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # M_31
], dtype=np.uint8)

SRSRAN_FEC_BLOCK_SIZE = 32
SRSRAN_FEC_BLOCK_MAX_NOF_BITS = 11


# ============================================================================
# CRC-8 Polynomial for long CQI encoding
# Polynomial: 0x9B (x^8 + x^7 + x^4 + x^3 + x + 1)
# ============================================================================
CRC8_POLY = 0x9B


def crc8_calculate(data: np.ndarray, num_bits: int) -> int:
    """
    Calculate 8-bit CRC for CQI encoding.

    Args:
        data: Input data bits (numpy array)
        num_bits: Number of input bits

    Returns:
        8-bit CRC value
    """
    crc = 0
    for i in range(num_bits):
        bit = int(data[i]) & 1
        crc = ((crc << 1) | bit) & 0x1FF
        if crc & 0x100:
            crc ^= CRC8_POLY

    # Shift remaining 8 bits
    for _ in range(8):
        crc = (crc << 1) & 0x1FF
        if crc & 0x100:
            crc ^= CRC8_POLY

    return int(crc & 0xFF)


def crc8_attach(data: np.ndarray, num_bits: int) -> np.ndarray:
    """
    Attach 8-bit CRC to data.

    Args:
        data: Input data bits
        num_bits: Number of input bits

    Returns:
        Data with CRC attached (num_bits + 8 bits)
    """
    crc = crc8_calculate(data, num_bits)
    output = np.zeros(num_bits + 8, dtype=np.uint8)
    output[:num_bits] = data[:num_bits]

    # Append CRC bits (MSB first)
    for i in range(8):
        output[num_bits + i] = (crc >> (7 - i)) & 1

    return output


# ============================================================================
# Block Code Encoder (32, O) for CQI <= 11 bits
# ============================================================================
def block_encode(input_bits: np.ndarray, input_len: int, output_len: int) -> np.ndarray:
    """
    Encode CQI bits using (32, O) block code with basis sequences.
    TS 36.212 Section 5.2.2.6.4

    Args:
        input_bits: Input CQI bits (max 11 bits)
        input_len: Number of input bits (O)
        output_len: Desired output length (Q)

    Returns:
        Encoded output bits
    """
    if input_len > SRSRAN_FEC_BLOCK_MAX_NOF_BITS or input_len == 0:
        raise ValueError(f"Input length must be 1-{SRSRAN_FEC_BLOCK_MAX_NOF_BITS}")

    # Generate 32-bit codeword: b_i = sum(o_n * M_i,n) mod 2
    codeword = np.zeros(SRSRAN_FEC_BLOCK_SIZE, dtype=np.uint8)
    for i in range(SRSRAN_FEC_BLOCK_SIZE):
        bit_sum = 0
        for n in range(input_len):
            bit_sum += input_bits[n] * M_BASIS_SEQ[i, n]
        codeword[i] = bit_sum % 2

    # Circular repetition to output length: q_i = b_(i mod 32)
    output = np.zeros(output_len, dtype=np.uint8)
    for i in range(output_len):
        output[i] = codeword[i % SRSRAN_FEC_BLOCK_SIZE]

    return output


# ============================================================================
# Tail-Biting Convolutional Encoder
# K=7, R=1/3, Polynomials: {0x6D, 0x4F, 0x57}
# ============================================================================
def convolutional_encode_tail_biting(data: np.ndarray, num_bits: int) -> np.ndarray:
    """
    Tail-biting convolutional encoder for LTE.
    Constraint length K=7, Rate R=1/3
    Polynomials: g0=0x6D (1101101), g1=0x4F (1001111), g2=0x57 (1010111)

    Args:
        data: Input data bits
        num_bits: Number of input bits

    Returns:
        Encoded bits (3 * num_bits)
    """
    # Polynomials in binary
    K = 7
    poly = [0x6D, 0x4F, 0x57]

    # Initialize shift register with last K-1 bits (tail biting)
    sr = 0
    for i in range(K - 1):
        if num_bits - (K - 1) + i >= 0:
            sr = (sr << 1) | (data[num_bits - (K - 1) + i] & 1)

    output = np.zeros(num_bits * 3, dtype=np.uint8)

    # Encode each input bit
    for i in range(num_bits):
        # Shift in new bit
        sr = ((sr << 1) | (data[i] & 1)) & 0x7F

        # Generate 3 output bits
        for j in range(3):
            # Compute parity
            temp = sr & poly[j]
            parity = 0
            while temp:
                parity ^= temp & 1
                temp >>= 1
            output[3 * i + j] = parity

    return output


# ============================================================================
# Rate Matching for Convolutional Coded CQI
# ============================================================================
def rate_match_conv(input_bits: np.ndarray, input_len: int, output_len: int) -> np.ndarray:
    """
    Rate matching for convolutional encoded CQI.
    Supports repetition (output_len > input_len) and puncturing (output_len < input_len).

    Args:
        input_bits: Convolutional encoded bits
        input_len: Length of input
        output_len: Desired output length (Q)

    Returns:
        Rate matched output
    """
    output = np.zeros(output_len, dtype=np.uint8)

    if output_len >= input_len:
        # Repetition
        for i in range(output_len):
            output[i] = input_bits[i % input_len]
    else:
        # Puncturing - systematic approach
        for i in range(output_len):
            idx = int((i * input_len) // output_len)
            output[i] = input_bits[idx]

    return output


# ============================================================================
# Long CQI Encoder (> 11 bits)
# ============================================================================
def encode_cqi_long(data: np.ndarray, nof_bits: int, Q: int) -> np.ndarray:
    """
    Encode CQI with more than 11 bits using CRC + convolutional coding + rate matching.
    TS 36.212 Section 5.2.3.2

    Args:
        data: Input CQI bits
        nof_bits: Number of CQI bits
        Q: Output length (Qm * Q'_CQI)

    Returns:
        Encoded CQI bits
    """
    # Step 1: Attach 8-bit CRC
    data_with_crc = crc8_attach(data, nof_bits)

    # Step 2: Convolutional encoding with tail biting
    encoded = convolutional_encode_tail_biting(data_with_crc, nof_bits + 8)

    # Step 3: Rate matching
    output = rate_match_conv(encoded, 3 * (nof_bits + 8), Q)

    return output


# ============================================================================
# Short CQI Encoder (<= 11 bits)
# ============================================================================
def encode_cqi_short(data: np.ndarray, nof_bits: int, Q: int) -> np.ndarray:
    """
    Encode CQI with 11 or fewer bits using (32, O) block code.
    TS 36.212 Section 5.2.2.6.4

    Args:
        data: Input CQI bits
        nof_bits: Number of CQI bits (1-11)
        Q: Output length

    Returns:
        Encoded CQI bits
    """
    return block_encode(data, nof_bits, Q)


# ============================================================================
# Modulation Order Mapping
# ============================================================================
def get_modulation_order(modulation: str) -> int:
    """Get bits per symbol (Qm) for modulation scheme."""
    mod_map = {
        'QPSK': 2,
        '16QAM': 4,
        '64QAM': 6,
        '256QAM': 8
    }
    if modulation not in mod_map:
        raise ValueError(f"Invalid modulation: {modulation}. Must be QPSK, 16QAM, 64QAM, or 256QAM")
    return mod_map[modulation]


# ============================================================================
# Parameter Expansion for Multiple Codewords
# ============================================================================
def expand_chs_params(chs: Dict) -> List[Dict]:
    """
    Expand CHS structure to handle multiple codewords.

    Args:
        chs: Channel configuration dictionary

    Returns:
        List of per-codeword configurations
    """
    # Check if parameters are lists (multi-codeword)
    if isinstance(chs.get('Modulation'), (list, tuple)):
        num_codewords = len(chs['Modulation'])
    else:
        num_codewords = 1

    configs = []
    for cw_idx in range(num_codewords):
        config = {}
        for key, value in chs.items():
            if isinstance(value, (list, tuple)) and len(value) == num_codewords:
                config[key] = value[cw_idx]
            else:
                config[key] = value
        configs.append(config)

    return configs


# ============================================================================
# Main lteCQIEncode Function
# ============================================================================
def lteCQIEncode(chs: Dict, input_data: Union[np.ndarray, List]) -> Union[np.ndarray, List]:
    """
    LTE CQI (Channel Quality Information) Encoder

    Encodes CQI bits according to TS 36.212 Sections 5.2.2.6 and 5.2.2.6.4.
    Compatible with MATLAB lteCQIEncode function.

    Args:
        chs: Channel configuration dictionary with fields:
            - QdCQI: Number of coded CQI symbols (Q'_CQI) [required]
                     Scalar for single codeword, list [Q1, Q2] for two codewords
            - Modulation: Modulation scheme [required]
                         String for single codeword: 'QPSK', '16QAM', '64QAM', '256QAM'
                         List for two codewords: ['16QAM', '64QAM']
            - NLayers: Number of transmission layers [optional, default=1]
                      Scalar (total layers) or per-codeword

        input_data: Input CQI bits
            - numpy array for single codeword
            - list of numpy arrays for multiple codewords (only one should have data)

    Returns:
        Encoded CQI bits:
            - numpy array (int8) for single codeword
            - list of numpy arrays for multiple codewords

    Examples:
        >>> # Single codeword
        >>> chs = {'Modulation': '16QAM', 'QdCQI': 4}
        >>> input_bits = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)
        >>> output = lteCQIEncode(chs, input_bits)

        >>> # Two codewords with CQI on second codeword
        >>> chs = {'Modulation': ['16QAM', '16QAM'], 'QdCQI': [0, 4], 'NLayers': 2}
        >>> input_bits = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)
        >>> output = lteCQIEncode(chs, input_bits)  # Returns [empty_array, encoded_array]
    """
    # Validate required parameters
    if 'QdCQI' not in chs:
        raise ValueError("Required parameter 'QdCQI' missing from chs structure")
    if 'Modulation' not in chs:
        raise ValueError("Required parameter 'Modulation' missing from chs structure")

    # Set default NLayers if not provided
    if 'NLayers' not in chs:
        chs['NLayers'] = 1

    # Expand parameters for multiple codewords
    configs = expand_chs_params(chs)
    num_codewords = len(configs)

    # Convert input to numpy array if needed
    if not isinstance(input_data, (list, tuple)):
        input_bits = np.array(input_data, dtype=np.uint8)
    else:
        input_bits = input_data

    # Process each codeword
    outputs = []

    for cw_idx, config in enumerate(configs):
        QdCQI = config['QdCQI']
        modulation = config['Modulation']

        # Skip codewords with QdCQI = 0
        if QdCQI == 0:
            outputs.append(np.array([], dtype=np.int8))
            continue

        # Get modulation order
        Qm = get_modulation_order(modulation)

        # Calculate output length Q = Qm * Q'_CQI
        Q = Qm * QdCQI

        # Get input bits for this codeword
        if num_codewords > 1 and isinstance(input_bits, (list, tuple)):
            cw_input = np.array(input_bits[cw_idx], dtype=np.uint8)
        else:
            cw_input = input_bits

        # Determine number of CQI bits
        O_cqi = len(cw_input)

        if O_cqi == 0:
            outputs.append(np.array([], dtype=np.int8))
            continue

        # Encode based on payload size
        if O_cqi <= 11:
            # Use (32, O) block code
            encoded = encode_cqi_short(cw_input, O_cqi, Q)
        else:
            # Use CRC + convolutional code + rate matching
            encoded = encode_cqi_long(cw_input, O_cqi, Q)

        # Convert to int8 (MATLAB compatible)
        outputs.append(encoded.astype(np.int8))

    # Return single array or list based on number of codewords
    if num_codewords == 1:
        return outputs[0]
    else:
        return outputs


# ============================================================================
# Test and Demo Functions
# ============================================================================
def test_lteCQIEncode():
    """Test cases matching MATLAB examples."""
    print("=" * 80)
    print("LTE CQI Encoder - Test Cases")
    print("=" * 80)

    # Test 1: Single codeword (MATLAB Example 1)
    print("\nTest 1: Single codeword encoding")
    print("-" * 40)
    input1 = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)
    chs1 = {
        'Modulation': '16QAM',
        'QdCQI': 4,
        'NLayers': 2
    }
    output1 = lteCQIEncode(chs1, input1)
    print(f"Input CQI bits: {input1}")
    print(f"CQI length: {len(input1)} bits")
    print(f"QdCQI: {chs1['QdCQI']}")
    print(f"Modulation: {chs1['Modulation']} (Qm=4)")
    print(f"Output length: {len(output1)} bits (Qm * QdCQI = 4 * 4 = 16)")
    print(f"Output: {output1}")
    print(f"Output dtype: {output1.dtype}")

    # Test 2: Two codewords with CQI on second codeword (MATLAB Example 2)
    print("\nTest 2: Two codewords, CQI on second codeword")
    print("-" * 40)
    input2 = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)
    chs2 = {
        'Modulation': ['16QAM', '16QAM'],
        'QdCQI': [0, 4],
        'NLayers': 2
    }
    output2 = lteCQIEncode(chs2, input2)
    print(f"Input CQI bits: {input2}")
    print(f"QdCQI: {chs2['QdCQI']} (CW0: 0, CW1: 4)")
    print(f"Output type: {type(output2)}")
    print(f"CW0 output: {output2[0]} (length: {len(output2[0])})")
    print(f"CW1 output: {output2[1]} (length: {len(output2[1])})")

    # Test 3: Long CQI (> 11 bits) with CRC and convolutional coding
    print("\nTest 3: Long CQI encoding (>11 bits)")
    print("-" * 40)
    input3 = np.array([1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1], dtype=np.uint8)
    chs3 = {
        'Modulation': '64QAM',
        'QdCQI': 10
    }
    output3 = lteCQIEncode(chs3, input3)
    print(f"Input CQI bits: {input3}")
    print(f"CQI length: {len(input3)} bits (>11, uses CRC+Conv)")
    print(f"QdCQI: {chs3['QdCQI']}")
    print(f"Modulation: {chs3['Modulation']} (Qm=6)")
    print(f"Output length: {len(output3)} bits (Qm * QdCQI = 6 * 10 = 60)")
    print(f"Encoding: CRC-8 + Tail-biting Conv (K=7,R=1/3) + Rate matching")

    # Test 4: Minimum CQI (1 bit)
    print("\nTest 4: Minimum CQI (1 bit)")
    print("-" * 40)
    input4 = np.array([1], dtype=np.uint8)
    chs4 = {
        'Modulation': 'QPSK',
        'QdCQI': 2
    }
    output4 = lteCQIEncode(chs4, input4)
    print(f"Input CQI bits: {input4}")
    print(f"Output length: {len(output4)} bits")
    print(f"Output: {output4}")

    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)


if __name__ == '__main__':
    test_lteCQIEncode()
