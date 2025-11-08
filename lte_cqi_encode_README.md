# LTE CQI Encoder - Python Implementation

A Python implementation of the LTE Channel Quality Indicator (CQI) encoder, compatible with MATLAB's `lteCQIEncode` function and based on srsRAN_4G implementation.

## Overview

This implementation follows **3GPP TS 36.212 Sections 5.2.2.6 and 5.2.2.6.4** for encoding Channel Quality Information (CQI) bits for LTE PUSCH transmission.

## Features

✅ **MATLAB-compatible interface** - Same syntax, input/output arguments, and data types
✅ **Dual encoding schemes**:
- **(32, O) Reed-Muller block code** for CQI ≤11 bits (Section 5.2.2.6.4)
- **CRC-8 + Tail-biting convolutional coding** for CQI >11 bits (Section 5.2.3.2)
✅ **Multiple codeword support** - Handles single and dual codeword configurations
✅ **Rate matching** - Repetition and puncturing for flexible output lengths
✅ **All modulation schemes** - QPSK, 16QAM, 64QAM, 256QAM

## Implementation Details

### Based on srsRAN_4G Code

The implementation is derived from:
- `lib/src/phy/fec/block/block.c` - (32, O) block code with 32 basis sequences
- `lib/src/phy/phch/uci.c` - CQI encoding functions
- `lib/src/phy/fec/convolutional/convcoder.c` - Tail-biting convolutional encoder

### Encoding Algorithms

#### Short CQI (≤11 bits): Block Code

```
b_i = Σ(o_n · M_i,n) mod 2  for i=0..31
q_i = b_(i mod 32)           for i=0..Q-1
```

Where:
- **M_i,n**: 32 basis sequences from TS 36.212 Table 5.2.2.6.4-1
- **O**: Number of input CQI bits (1-11)
- **Q**: Output length = Qm × Q'_CQI

#### Long CQI (>11 bits): CRC + Convolutional

1. **CRC-8 attachment** - Polynomial: 0x9B (x⁸+x⁷+x⁴+x³+x+1)
2. **Tail-biting convolutional encoding**:
   - Constraint length K=7
   - Rate R=1/3
   - Generator polynomials: {0x6D, 0x4F, 0x57}
3. **Rate matching** - Repetition or puncturing to match Q output symbols

## Usage

### Syntax

```python
output = lteCQIEncode(chs, input_data)
```

### Parameters

#### Input: `chs` (dict)

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `QdCQI` | ✓ | int or list | Number of coded CQI symbols (Q'_CQI) |
| `Modulation` | ✓ | str or list | Modulation: 'QPSK', '16QAM', '64QAM', '256QAM' |
| `NLayers` | Optional | int | Number of transmission layers (default=1) |

#### Input: `input_data`

- **Single codeword**: numpy array of CQI bits (uint8)
- **Multiple codewords**: list of numpy arrays

#### Output

- **Single codeword**: numpy array of encoded bits (int8)
- **Multiple codewords**: list of numpy arrays

## Examples

### Example 1: Single Codeword (6 CQI bits)

```python
import numpy as np
from lte_cqi_encode import lteCQIEncode

# Input CQI bits
input_bits = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)

# Configuration
chs = {
    'Modulation': '16QAM',    # Qm = 4 bits/symbol
    'QdCQI': 4,               # Q'_CQI = 4 coded symbols
    'NLayers': 2
}

# Encode
output = lteCQIEncode(chs, input_bits)
# Output: 16 bits (Qm × Q'_CQI = 4 × 4 = 16)
```

**Expected Output:**
```
[1 1 1 1 0 1 0 1 0 1 1 0 0 1 1 0]
```

### Example 2: Two Codewords (CQI on Second)

```python
# Input CQI bits
input_bits = np.array([0, 1, 0, 1, 0, 1], dtype=np.uint8)

# Configuration for 2 codewords
chs = {
    'Modulation': ['16QAM', '16QAM'],
    'QdCQI': [0, 4],          # CQI on codeword 1 only
    'NLayers': 2
}

# Encode
output = lteCQIEncode(chs, input_bits)
# Returns: [empty_array, encoded_array]
```

**Output:**
```python
[array([], dtype=int8),
 array([1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0], dtype=int8)]
```

### Example 3: Long CQI (>11 bits with CRC+Conv)

```python
# 15 CQI bits (requires CRC + convolutional coding)
input_bits = np.array([1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1], dtype=np.uint8)

chs = {
    'Modulation': '64QAM',    # Qm = 6 bits/symbol
    'QdCQI': 10               # Q'_CQI = 10 coded symbols
}

# Encode
output = lteCQIEncode(chs, input_bits)
# Output: 60 bits (6 × 10)
# Uses: CRC-8 attachment + tail-biting conv + rate matching
```

### Example 4: Minimum CQI (1 bit)

```python
input_bits = np.array([1], dtype=np.uint8)

chs = {
    'Modulation': 'QPSK',     # Qm = 2 bits/symbol
    'QdCQI': 2                # Q'_CQI = 2 coded symbols
}

output = lteCQIEncode(chs, input_bits)
# Output: [1 1 1 1] (4 bits)
```

## Algorithm Flow

```
Input CQI bits (O bits)
        |
        v
   [O ≤ 11?]
        |
   Yes  |  No
        |
   [Block Code]        [CRC-8 Attach] → (O+8 bits)
   (32,O) encoder              |
        |                      v
        |              [Tail-biting Conv]
        |              K=7, R=1/3 encoder → (3×(O+8) bits)
        |                      |
        v                      v
   [Circular Rep]      [Rate Matching]
        |                      |
        v                      v
   Output (Q bits)    Output (Q bits)
```

## Basis Sequences (Table 5.2.2.6.4-1)

The 32 basis sequences M_i,n are defined per TS 36.212:

```
M_0  = [1 1 0 0 0 0 0 0 0 0 1]
M_1  = [1 1 1 0 0 0 0 0 0 1 1]
M_2  = [1 0 0 1 0 0 1 0 1 1 1]
...
M_30 = [1 1 1 1 1 1 1 1 1 1 1]
M_31 = [1 0 0 0 0 0 0 0 0 0 0]
```

All 32 sequences are stored in the `M_BASIS_SEQ` constant.

## Technical Specifications

### Block Code Parameters
- **Code type**: (32, O) Reed-Muller
- **Input size**: O = 1 to 11 bits
- **Codeword size**: 32 bits
- **Output**: Circular repetition to Q bits

### Convolutional Code Parameters
- **Constraint length**: K = 7
- **Code rate**: R = 1/3
- **Tail biting**: Enabled (circular trellis)
- **Polynomials**:
  - g₀ = 0x6D (1101101₂)
  - g₁ = 0x4F (1001111₂)
  - g₂ = 0x57 (1010111₂)

### CRC Parameters
- **CRC width**: 8 bits
- **Polynomial**: 0x9B (x⁸+x⁷+x⁴+x³+x+1)
- **Applies to**: CQI payloads > 11 bits

### Modulation Mapping
| Modulation | Qm (bits/symbol) |
|------------|------------------|
| QPSK       | 2 |
| 16QAM      | 4 |
| 64QAM      | 6 |
| 256QAM     | 8 |

## Validation

The implementation has been tested against:
- ✅ MATLAB LTE Toolbox examples
- ✅ srsRAN_4G reference implementation
- ✅ 3GPP TS 36.212 specifications
- ✅ Edge cases (1 bit, 11 bits, 12+ bits)
- ✅ Multiple codeword scenarios

## Comparison with srsRAN_4G

| Feature | srsRAN_4G (C) | This Implementation (Python) |
|---------|---------------|------------------------------|
| Block code | ✓ `block.c:srsran_block_encode()` | ✓ `block_encode()` |
| CRC-8 | ✓ `crc.c:srsran_crc_attach()` | ✓ `crc8_attach()` |
| Conv encoder | ✓ `convcoder.c:srsran_convcoder_encode()` | ✓ `convolutional_encode_tail_biting()` |
| Rate matching | ✓ `rm_conv.c:srsran_rm_conv_tx()` | ✓ `rate_match_conv()` |
| Multi-CW | ✓ Supported | ✓ Supported |
| Optimizations | SSE/AVX2 | Pure Python (portable) |

## Dependencies

- **Python**: 3.7+
- **NumPy**: For array operations and MATLAB compatibility

## Installation

```bash
pip install numpy
```

## Running Tests

```bash
python3 lte_cqi_encode.py
```

## File Structure

```
lte_cqi_encode.py           # Main implementation
├── M_BASIS_SEQ             # 32 basis sequences table
├── crc8_calculate()        # CRC-8 computation
├── crc8_attach()           # CRC attachment
├── block_encode()          # (32,O) block encoder
├── convolutional_encode_tail_biting()  # Conv encoder
├── rate_match_conv()       # Rate matching
├── encode_cqi_short()      # Short CQI (≤11 bits)
├── encode_cqi_long()       # Long CQI (>11 bits)
├── lteCQIEncode()          # Main MATLAB-compatible API
└── test_lteCQIEncode()     # Test suite
```

## Standards Compliance

- **3GPP TS 36.212 V10.0.0** (2011-03): Multiplexing and channel coding
  - Section 5.2.2.6: UCI on PUSCH
  - Section 5.2.2.6.4: (32, O) block code
  - Section 5.2.3.2: CRC attachment
  - Section 5.1.3.1: Tail-biting convolutional code

## References

1. **3GPP TS 36.212**: "Evolved Universal Terrestrial Radio Access (E-UTRA); Multiplexing and channel coding"
2. **srsRAN_4G**: https://github.com/srsRAN/srsRAN_4G
3. **MATLAB LTE Toolbox**: Communications Toolbox documentation

## License

Compatible with srsRAN_4G licensing (GNU Affero General Public License v3.0)

## Author

Implementation based on srsRAN_4G reference code and 3GPP specifications.

---

**Note**: This is a reference implementation optimized for correctness and MATLAB compatibility, not for real-time performance. For production LTE systems, use srsRAN_4G's optimized C implementation.
