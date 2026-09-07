"""Relevance scoring for the decal search box - see routes.index for how this plugs into the existing filters/sort."""

import difflib
import re

from .models import LANGUAGES

_LANGUAGE_NAMES = dict(LANGUAGES)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_TO_SPACE_RE = re.compile(r"[^a-z0-9\s]")

# Relevance tiers, highest first - named constants keep the priority order
# visible in one place instead of scattered through _score_term.
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
# Added on top of a multi-term match when the query is also an exact phrase.
PHRASE_MATCH_BONUS = 20

# difflib ratio below which two words count as unrelated, not a typo.
_FUZZY_RATIO_THRESHOLD = 0.78
# Words shorter than this are never fuzzy-matched (too many near-neighbors,
# and it keeps fuzzy matching away from short identifier fragments).
_FUZZY_MIN_WORD_LENGTH = 4


def normalize_identifier(value):
    """Lowercase and strip non-alphanumerics, so "175-1042-2"/"175 1042 2"/"17510422" compare equal."""
    if not value:
        return ""
    return _NON_ALNUM_RE.sub("", value.lower())


def normalize_text(value):
    """Lowercase and collapse whitespace, for natural-language fields."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def normalize_phrase(value):
    """Like normalize_identifier but keeps words separate (spaces, not concatenated), preserving word order for phrase matching."""
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
    """Exact or fuzzy substring score for one term against one text field."""
    if not field_text or not term:
        return 0
    if term in field_text:
        return exact_score
    if _fuzzy_word_in_text(term, field_text.split()):
        return fuzzy_score
    return 0


def _decal_context(decal):
    """Precompute one decal's normalized fields, once per decal per search."""
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
        # Punctuation-insensitive versions, used only for the phrase bonus.
        "description_phrase": normalize_phrase(decal.description),
        "notes_phrase": normalize_phrase(decal.notes),
        "subcategory_phrase": normalize_phrase(" ".join(sc.subcategory for sc in decal.subcategories)),
    }


def _score_term(context, term):
    """Highest matching tier for one search term against one decal; fuzzy matching never applies to part/model identifiers, only text fields."""
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
    """PHRASE_MATCH_BONUS if the query's words appear together, in order, in one field, else 0 - no fuzzy matching, since this only boosts an already-established AND match."""
    if not query_phrase:
        return 0
    for field_key in _PHRASE_FIELD_KEYS:
        if query_phrase in context[field_key]:
            return PHRASE_MATCH_BONUS
    return 0


def score_decal(decal, query):
    """Score one decal against a query (average of per-term scores, all terms required, plus phrase bonus) - a single-decal convenience; rank_decals decides AND-vs-fallback across a result set."""
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
    """Score, filter, and sort decals: terms are ANDed (falling back to whichever decals matched the most, if none match all), ranked by average term score plus phrase bonus, then part number."""
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
