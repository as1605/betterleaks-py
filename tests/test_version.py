import betterleaks


def test_version():
    assert betterleaks.__version__ == "2.0.0rc4"
    assert betterleaks.__upstream_version__ == "2.0.0-rc.4"
