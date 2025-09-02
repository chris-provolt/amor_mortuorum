from amor.core.seed import SeedManager


def test_seed_manager_determinism_same_seed():
    sm1 = SeedManager(12345)
    sm2 = SeedManager(12345)
    seq1 = [sm1.randint(0, 1000) for _ in range(10)]
    seq2 = [sm2.randint(0, 1000) for _ in range(10)]
    assert seq1 == seq2


def test_seed_manager_differing_seeds():
    sm1 = SeedManager(1)
    sm2 = SeedManager(2)
    seq1 = [sm1.randint(0, 100) for _ in range(5)]
    seq2 = [sm2.randint(0, 100) for _ in range(5)]
    assert seq1 != seq2


def test_temporary_seed_restores_state():
    sm = SeedManager(42)
    base_seq = [sm.randint(0, 100) for _ in range(3)]
    with sm.temporary_seed(42):
        _ = [sm.randint(0, 100) for _ in range(5)]
    # After context, continue sequence as if uninterrupted
    cont_seq = [sm.randint(0, 100) for _ in range(3)]
    sm2 = SeedManager(42)
    expected = [sm2.randint(0, 100) for _ in range(6)][3:]
    assert cont_seq == expected


def test_derive_seed_from_string_stable():
    sm = SeedManager()
    s1 = sm.derive_seed("floor-001")
    s2 = sm.derive_seed("floor-001")
    s3 = sm.derive_seed("floor-002")
    assert s1 == s2
    assert s1 != s3


def test_deterministic_uuid4_stable():
    sm = SeedManager(10)
    u1 = sm.deterministic_uuid4()
    sm2 = SeedManager(10)
    u2 = sm2.deterministic_uuid4()
    assert str(u1) == str(u2)
