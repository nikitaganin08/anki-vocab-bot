from app.services.answer_check import auto_rating, build_prompt, check_answer

PREFIXES = ("to ", "a ", "an ", "the ")


def test_exact_match_case_insensitive() -> None:
    result = check_answer("  Give   UP. ", "give up")

    assert result.verdict == "correct"
    assert result.expected == "give up"


def test_one_typo_long_word_is_typo() -> None:
    assert check_answer("reluctnat", "reluctant").verdict == "typo"
    assert check_answer("reluctan", "reluctant").verdict == "typo"


def test_one_typo_short_word_is_wrong() -> None:
    assert check_answer("giv", "give").verdict == "wrong"


def test_two_typos_is_wrong() -> None:
    assert check_answer("relutcnat", "reluctant").verdict == "wrong"


def test_russian_layout_converted() -> None:
    assert check_answer("пшму гз", "give up").verdict == "correct"
    assert check_answer("ПШМУ ГЗ", "give up").verdict == "correct"
    assert check_answer("вщтэе", "don't").verdict == "correct"


def test_curly_apostrophe() -> None:
    assert check_answer("don’t", "don't").verdict == "correct"
    assert check_answer("don't", "don’t").verdict == "correct"


def test_optional_to_prefix() -> None:
    assert check_answer("to give up", "give up", optional_prefixes=PREFIXES).verdict == "correct"
    assert check_answer("give up", "to give up", optional_prefixes=PREFIXES).verdict == "correct"
    assert check_answer("to give up", "give up").verdict == "wrong"


def test_empty_is_wrong() -> None:
    assert check_answer("", "give up").verdict == "wrong"
    assert check_answer("  ?! ", "give up").verdict == "wrong"


def test_auto_rating_matrix() -> None:
    assert auto_rating("wrong", hint_used=False) == 1
    assert auto_rating("wrong", hint_used=True) == 1
    assert auto_rating("correct", hint_used=True) == 2
    assert auto_rating("typo", hint_used=True) == 2
    assert auto_rating("typo", hint_used=False) == 3
    assert auto_rating("correct", hint_used=False) == 3


CHUNKS = [
    {"text": "give up smoking", "target": "give up", "translation": "бросить курить"},
    {"text": "never gave up", "target": "gave up", "translation": "никогда не сдавался"},
]


def test_build_prompt_rotates_chunks() -> None:
    indexes = [build_prompt(CHUNKS, ["сдаваться"], "give up", n).index for n in (0, 1, 2)]
    prompt = build_prompt(CHUNKS, ["сдаваться"], "give up", 1)

    assert indexes == [0, 1, 0]
    assert prompt.kind == "chunk"
    assert prompt.masked == "never ___"
    assert prompt.hint_translation == "никогда не сдавался"
    assert prompt.expected == "gave up"


def test_build_prompt_masks_first_case_insensitive() -> None:
    chunks = [{"text": "Give up and give up", "target": "give up", "translation": "сдаться"}]

    prompt = build_prompt(chunks, ["сдаваться"], "give up", 0)

    assert prompt.masked == "___ and give up"
    assert prompt.expected == "Give up"


def test_build_prompt_falls_back_to_translation() -> None:
    prompt = build_prompt([], ["сдаваться", "бросать"], "give up", 7)

    assert prompt.kind == "translation"
    assert prompt.index == 0
    assert prompt.masked == "сдаваться, бросать"
    assert prompt.expected == "give up"
