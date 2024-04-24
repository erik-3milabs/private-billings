from private_billing import Int64ToFloatConvertor


def test_format():
    conv = Int64ToFloatConvertor(4, 4)

    val = conv.convert_from_int64(1234_5678)
    assert val == 1234.5678


def test_removes_extra():
    conv = Int64ToFloatConvertor(4, 4)

    val = conv.convert_from_int64(1_1000_0000)
    assert val == 1000.0000


def test_maintains_sign():
    conv = Int64ToFloatConvertor(4, 4)

    val = conv.convert_from_int64(-1000_0000)
    assert val == -1000
