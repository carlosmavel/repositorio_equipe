from core.services.article_versions import (
    calculate_plain_text_char_count,
    calculate_reduction_percent,
    is_drastic_content_reduction,
)


def test_plain_text_char_count_strips_html_and_normalizes_space():
    assert calculate_plain_text_char_count('<p>Olá&nbsp; <strong>mundo</strong></p>') == len('Olá mundo')


def test_reduction_percent_and_drastic_thresholds():
    reduction_percent = calculate_reduction_percent(1000, 250)

    assert reduction_percent == 75
    assert is_drastic_content_reduction(1000, 250, reduction_percent) is True
    assert is_drastic_content_reduction(2500, 299, None) is True
