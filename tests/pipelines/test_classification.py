from cyberpunk_stats.pipelines.classification.nodes import max_burst


def test_max_burst():
    assert max_burst([1, 2, 3, 4, 100], anchors=[3], window_s=60) == 4
    assert max_burst([1, 2, 3, 4, 100], anchors=[100], window_s=60) == 1  # burst must include an anchor
    assert max_burst([0, 61, 62], anchors=[0], window_s=60) == 1
