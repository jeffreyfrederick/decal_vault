"""Search normalization and relevance scoring for the decal browse page.

SQLite/SQLAlchemy has no built-in fuzzy or format-insensitive matching, and
the number of decals is small (entered by hand by documentation staff), so
scoring candidates in Python after a normal SQLAlchemy query is simpler to
reason about than adding SQLite FTS5 or an external search dependency.

A query is split into whitespace-separated terms and treated as an AND:
each term is scored against a decal independently (see _score_term), and
rank_decals only prefers decals that match every term, falling back to
whichever decals matched the most terms if none match all of them. Scoring
terms independently - rather than scoring the query as one string - matters
for multi-word queries: normalizing "tcx50 shock" as a whole would strip the
space and read as "tcx50shock", which happens to contain "tcx50" as a
substring regardless of whether "shock" appears anywhere on the decal.

On top of that term-level AND, a query of more than one term also gets a
phrase check: if the words appear in the same order, adjacent, in one
field (e.g. "back of device" literally in a description), that decal gets
a bonus on top of its term-average score - see _phrase_match_bonus. This
only ever adds to the term-based score, so it can't be the reason a decal
matches; a decal still has to satisfy the AND requirement first.

See routes.index for how this plugs into the existing category/model/
language/status filters and sort.
"""

import difflib
import re

from .models import LANGUAGES

_LANGUAGE_NAMES = dict(LANGUAGES)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_TO_SPACE_RE = re.compile(r"[^a-z0-9\s]")

# Relevance tiers, highest first, matching the priority order the search is
# meant to follow: part number, then model, then progressively looser text
# matches. Named constants keep that order visible in one place instead of
# scattered through _score_term.
SCORE_PART_NUMBER_EXACT = 100
SCORE_MODEL_EXACT = 90
SCORE_IDENTIFIER_NORMALIZED_EXACT = 80
SCORE_IDENTIFIER_PARTIAL = 70
SCORE_IDENTIFIER_PARTIAL_REVERSE = 65
SCORE_DESCRIPTION_EXACT = 60
SCORE_DESCRIPTION_FUZZY = 55
SCORE_CATEGORY_LANGUAGE_EXACT = 50
SCORE_CATEGORY_LANGUAGE_PARTIAL = 45
SCORE_OTHER_TEXT_EXACT = 40
SCORE_OTHER_TEXT_FUZZY = 35

# Added on top of a multi-term query's combined score when the whole query
# appears as an exact, in-order phrase in one field (see _phrase_match_bonus)
# - not a tier of its own, since it only ever boosts an existing AND match.
PHRASE_MATCH_BONUS = 20

# Below this difflib ratio, two words are treated as unrelated rather than a
# typo of one another - tuned so "rotatonal" matches "rotational" without
# starting to match unrelated words.
_FUZZY_RATIO_THRESHOLD = 0.78
# Words shorter than this are never fuzzy-matched: short strings have too
# many near neighbors for a similarity ratio to mean anything, and this also
# keeps fuzzy matching away from short part-number-like fragments.
_FUZZY_MIN_WORD_LENGTH = 4


def normalize_identifier(value):
    """Lowercase and drop everything but letters/digits.

    Used for part numbers and model numbers so "175-1042-2", "175 1042 2",
    and "17510422" all compare equal. Only affects the search/compare step -
    stored values are never touched.
    """
    if not value:
        return ""
    return _NON_ALNUM_RE.sub("", value.lower())


def normalize_text(value):
    """Lowercase and collapse whitespace, for natural-language fields."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def normalize_phrase(value):
    """Lowercase, collapse whitespace, and turn punctuation into spaces -
    for exact-phrase comparison. Unlike normalize_identifier, this keeps
    words separate (never concatenates them), so word order is preserved
    and "back-of-device"/"back, of device"/"Back of Device" all normalize
    to the same "back of device" for a substring check.
    """
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", _NON_ALNUM_TO_SPACE_RE.sub(" ", value.lower())).strip()


def _fuzzy_word_in_text(term, text_words):
    if len(term) < _FUZZY_MIN_WORD_LENGTH:
        return False
    for word in text_words:
        if len(word) < _FUZZY_MIN_WORD_LENGTH:
            continue
        if difflib.SequenceMatcher(None, term, word).ratio() >= _FUZZY_RATIO_THRESHOLD:
            return True
    return False


def _text_field_score(term, field_text, exact_score, fuzzy_score):
    """Score one natural-language field (description/notes/...) against a
    single search term. Returns exact_score for a verbatim substring match,
    fuzzy_score for a close (typo) variant, otherwise 0.
    """
    if not field_text or not term:
        return 0
    if term in field_text:
        return exact_score
    if _fuzzy_word_in_text(term, field_text.split()):
        return fuzzy_score
    return 0


def _decal_context(decal):
    """Precompute one decal's normalized, searchable fields.

    Computed once per decal per search rather than once per (decal, term)
    pair, since a multi-term query scores the same decal repeatedly.
    """
    part_number = decal.part_number or ""
    model_names = [m.name for m in decal.models]
    languages = {normalize_text(decal.language), normalize_text(_LANGUAGE_NAMES.get(decal.language, ""))}
    languages.discard("")
    return {
        "part_number": part_number,
        "part_id": normalize_identifier(part_number),
        "model_names": model_names,
        "model_ids": [normalize_identifier(name) for name in model_names],
        "categories": {normalize_text(m.category) for m in decal.models},
        "languages": languages,
        "description": normalize_text(decal.description),
        "notes": normalize_text(decal.notes),
        "subcategory_text": normalize_text(" ".join(sc.subcategory for sc in decal.subcategories)),
        # Punctuation-insensitive versions of the same free-text fields, used
        # only for the exact-phrase bonus (see _phrase_match_bonus).
        "description_phrase": normalize_phrase(decal.description),
        "notes_phrase": normalize_phrase(decal.notes),
        "subcategory_phrase": normalize_phrase(" ".join(sc.subcategory for sc in decal.subcategories)),
    }


def _score_term(context, term):
    """Relevance score for a single search term against one decal's fields.

    Higher is more relevant; 0 means the term doesn't appear anywhere on the
    decal. Checks run in priority order (part number, then model, then
    looser text matches) and return as soon as a tier matches, so the score
    reflects the *best* reason this term matched rather than a sum across
    fields.

    Fuzzy (typo-tolerant) matching only applies to natural-language fields
    (description, notes, subcategories, category/language names) - never to
    part numbers or model numbers, where a near-miss should not silently
    surface a different physical part.
    """
    term_lower = term.lower()
    term_id = normalize_identifier(term)
    term_text = normalize_text(term)

    if context["part_number"].lower() == term_lower:
        return SCORE_PART_NUMBER_EXACT

    if term_lower in (name.lower() for name in context["model_names"]):
        return SCORE_MODEL_EXACT

    part_id = context["part_id"]
    model_ids = context["model_ids"]
    if term_id and (term_id == part_id or term_id in model_ids):
        return SCORE_IDENTIFIER_NORMALIZED_EXACT

    if term_id and len(term_id) >= 2:
        if (part_id and term_id in part_id) or any(term_id in model_id for model_id in model_ids if model_id):
            return SCORE_IDENTIFIER_PARTIAL
        if (part_id and part_id in term_id) or any(model_id and model_id in term_id for model_id in model_ids):
            return SCORE_IDENTIFIER_PARTIAL_REVERSE

    description_score = _text_field_score(term_text, context["description"], SCORE_DESCRIPTION_EXACT, SCORE_DESCRIPTION_FUZZY)
    if description_score:
        return description_score

    if term_text in context["categories"] or term_text in context["languages"]:
        return SCORE_CATEGORY_LANGUAGE_EXACT
    if term_text and any(term_text in value for value in context["categories"] | context["languages"]):
        return SCORE_CATEGORY_LANGUAGE_PARTIAL

    notes_score = _text_field_score(term_text, context["notes"], SCORE_OTHER_TEXT_EXACT, SCORE_OTHER_TEXT_FUZZY)
    if notes_score:
        return notes_score

    return _text_field_score(term_text, context["subcategory_text"], SCORE_OTHER_TEXT_EXACT, SCORE_OTHER_TEXT_FUZZY)


_PHRASE_FIELD_KEYS = ("description_phrase", "notes_phrase", "subcategory_phrase")


def _phrase_match_bonus(query_phrase, context):
    """PHRASE_MATCH_BONUS if the query's words appear together, in order, in
    one field; 0 otherwise. query_phrase is expected to already be
    normalize_phrase()'d.

    This deliberately doesn't fuzzy-match: it's a bonus on top of a match
    the term-level AND has already established, not a new way to match, so
    there's no typo-tolerance requirement to satisfy here.
    """
    if not query_phrase:
        return 0
    for field_key in _PHRASE_FIELD_KEYS:
        if query_phrase in context[field_key]:
            return PHRASE_MATCH_BONUS
    return 0


def score_decal(decal, query):
    """Combined relevance score for one decal against a whole query.

    A multi-term query only scores above 0 here if every term matches
    somewhere on the decal (the term scores are averaged, then boosted if
    the query also appears as an exact phrase - see _phrase_match_bonus).
    This is a convenience for scoring one decal in isolation; rank_decals is
    what actually decides, across a whole result set, whether to require
    every term or fall back to partial coverage - see its docstring.
    """
    terms = normalize_text(query).split()
    if not terms:
        return 0
    context = _decal_context(decal)
    term_scores = [_score_term(context, term) for term in terms]
    if any(score == 0 for score in term_scores):
        return 0
    score = sum(term_scores) / len(term_scores)
    if len(terms) > 1:
        score += _phrase_match_bonus(normalize_phrase(query), context)
    return score


def rank_decals(decals, query):
    """Score, filter, and sort decals against a free-text search query.

    Terms (whitespace-separated words in the query) are ANDed together: a
    decal ranks among the results only if it matches every term, so adding
    a word narrows the results instead of just nudging relevance order.
    If no decal matches every term, this falls back to whichever decals
    matched the most terms - e.g. for "tcx50 zzz" with no decal matching
    "zzz" anywhere, decals matching "tcx50" alone are shown rather than
    nothing at all - but a decal matching only one of several terms is never
    shown if some other decal matches more of them.

    Within a coverage group, decals are ranked by the average score of
    their matched terms plus a phrase-match bonus (see _phrase_match_bonus),
    then by part number for a stable order. A decal with every term
    scattered across different fields and one with the exact phrase both
    satisfy the AND requirement the same way, but the phrase bonus pushes
    the latter to the top - e.g. for "back of device", a description that
    literally reads "Back of Device" outranks one that just happens to
    mention "back", "of", and "device" separately.
    """
    terms = normalize_text(query).split()
    if not terms:
        return []
    query_phrase = normalize_phrase(query) if len(terms) > 1 else ""

    scored = []
    for decal in decals:
        context = _decal_context(decal)
        term_scores = [_score_term(context, term) for term in terms]
        matched_terms = sum(1 for term_score in term_scores if term_score > 0)
        phrase_bonus = _phrase_match_bonus(query_phrase, context)
        scored.append((decal, term_scores, matched_terms, phrase_bonus))

    best_coverage = max((matched for _, _, matched, _ in scored), default=0)
    if best_coverage == 0:
        return []

    def combined_score(term_scores, phrase_bonus):
        matched_scores = [term_score for term_score in term_scores if term_score > 0]
        return sum(matched_scores) / len(matched_scores) + phrase_bonus

    finalists = [
        (decal, term_scores, phrase_bonus)
        for decal, term_scores, matched, phrase_bonus in scored
        if matched == best_coverage
    ]
    finalists.sort(key=lambda item: (-combined_score(item[1], item[2]), item[0].part_number or ""))
    return [decal for decal, _, _ in finalists]
