"""Labelled cases for the two judgements this scanner actually makes:
is this story the same as one already shown, and is this source worth reading.

These are not illustrative. Every case here is one the scanner previously got
wrong, or a control that guards a fix from overreaching. The controls matter
more than the duplicates: a surviving duplicate costs a line on a page, a wrong
merge deletes a story you needed to see. So there are deliberately more "these
must stay separate" cases than "these must collapse".

Run: python tests/test_signals.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from scan import same_story, distinctive                          # noqa: E402
from sources import (_news_score, _material, _source_weight,      # noqa: E402
                     worth_alerting, worth_reading, worth_translating,
                     detect_language, match_short)
from translate import clean, DeepL, Azure                         # noqa: E402

# (subject, headline A, headline B, should_merge, description)
STORY_CASES = [
    # Same event, different wording or language. These must collapse.
    ("Aker BP", "Equinor, Aker BP and Vår Energi join forces to search for Norway",
     "Equinor, Aker BP og Vår Energi går sammen for å lete etter Norge",
     True, "one filing, Norwegian and English"),
    ("Aker BP", "Equinor, Aker BP and Vår Energi join forces to search for Norway",
     "Equinor, Aker BP and Vaar target major Norway oil, gas discoveries",
     True, "filing and the wire report of it"),
    ("Sandvik", "SEB sees strong growth prospects for Sandvik, upgrades to buy",
     "Sandvik stock climbs after SEB rating upgrade and higher price target",
     True, "one upgrade, two outlets"),
    ("Infineon", "Infineon acquires Bangalore-based C2i Semiconductors",
     "Infineon Technologies acquires C2i Semiconductors to expand into",
     True, "one deal, two outlets"),
    ("SAP", "SAP raises cloud revenue outlook for 2026",
     "SAP lifts cloud guidance after strong quarter",
     True, "raises/lifts and outlook/guidance are synonyms"),
    ("Volvo", "Volvo cuts truck delivery outlook for 2026",
     "Volvo lowers guidance on European truck demand",
     True, "cuts/lowers likewise"),
    ("Embracer", "Embracer to split into three listed companies",
     "Embracer announces three-way separation of group",
     True, "split and separation are one event"),
    ("Yara", "Yara halts ammonia production at Tertre on gas prices",
     "Yara to close Tertre ammonia plant permanently",
     True, "same site, escalating"),

    # Controls. A merge here would hide something.
    ("Infineon", "Infineon acquires Bangalore-based C2i Semiconductors",
     "Infineon cuts full-year revenue guidance on weak auto demand",
     False, "an acquisition is not a guidance cut"),
    ("SAP", "SAP raises cloud revenue outlook for 2026",
     "SAP cuts cloud revenue outlook for 2026",
     False, "opposite directions are never one story"),
    ("Yara", "Yara halts ammonia production at Tertre",
     "Yara halts ammonia production at Sluiskil",
     False, "same act, different plant"),
    ("Subsea 7", "Subsea 7 awarded large contract offshore Brazil",
     "Subsea 7 awarded large contract offshore Angola",
     False, "same act, different country"),
    ("Airbus", "Airbus wins 40-jet order from Lufthansa",
     "Airbus wins 40-jet order from IndiGo",
     False, "same act, different customer"),
    ("Sandvik", "SEB sees strong growth prospects for Sandvik, upgrades to buy",
     "Sandvik wins 900 million SEK mining order in Chile",
     False, "an upgrade is not an order win"),
    ("Aker BP", "Equinor, Aker BP and Vår Energi join forces to search for Norway",
     "Aker BP cuts 2026 capex guidance after Johan Sverdrup review",
     False, "a discovery is not a capex cut"),
    ("ASML", "ASML reports transactions under its current share buyback programme",
     "ASML wins export licence for China shipments",
     False, "a buyback is not an export licence"),
    ("Volvo", "Volvo B: Interim report January-June 2026",
     "Volvo delivers record truck orders in North America",
     False, "a report is not an order book"),
    ("ASML", "ASML Q2 bookings beat expectations",
     "ASML names new chief financial officer",
     False, "results are not an appointment"),
    # Isolates dropping the subject name. These share the company plus one
    # incidental verb; keeping the name would push them over the threshold and
    # merge two unrelated stories.
    ("Airbus", "Airbus delivers 60 jets in July",
     "Airbus delivers new emissions plan to regulators",
     False, "company name plus a coincidental verb is not a shared story"),
    ("Yara", "Yara reports second quarter results",
     "Yara reports fire at Porsgrunn plant",
     False, "likewise - 'reports' is not a story"),
]

# (headline, publisher, predicate, description)
SCORE_CASES = [
    (lambda s: s >= 2, "Equinor, Aker BP make gas find just northwest of Balder field",
     "Reuters", "a wire reporting a discovery"),
    (lambda s: s >= 2, "Infineon acquires Bangalore-based C2i Semiconductors",
     "Evertiq", "an acquisition from trade press"),
    (lambda s: s >= 2, "Volvo wins 900 million SEK order", "Financial Times",
     "FT keeps its weight through the flattened lookup"),
    (lambda s: s < 0, "Infineon's Stock Trades at a 39% Discount to Its High",
     "Ad-hoc-news.de", "valuation arithmetic, not news"),
    (lambda s: s < 0, "ASML: 5 Things You Need To Know", "simplywall.st",
     "content farm - and the dotted name must still match its key"),
    (lambda s: s < 0, "Sandvik shares gap up after strong quarter", "Benzinga",
     "chart commentary"),
    (lambda s: s < 2, "SEB sees strong growth prospects for Sandvik, upgrades to buy",
     "marketscreener.com", "real story, demoted aggregator: another outlet should carry it"),
    # Isolates the junk patterns. Electronics Weekly carries no weight of its
    # own, so only the headline pattern can push these below the threshold.
    (lambda s: s < 0, "Infineon's Stock Trades at a 39% Discount to Its High",
     "Electronics Weekly", "valuation commentary from a neutral publisher"),
    (lambda s: s < 0, "Here's Why ASML Stock Is Worth Buying Today",
     "Electronics Weekly", "opinion framing from a neutral publisher"),
    (lambda s: s >= 2, "Infineon wins design order from Bosch",
     "Electronics Weekly", "control: neutral publisher, real news, still passes"),
]


# (should_alert, headline, publisher, description)
ALERT_CASES = [
    # A material event clears even from a weak outlet - only aggregators cover
    # single-broker notes on mid-caps, and the note is still a fact.
    (True, "SEB upgrades Sandvik to buy (hold), target price 445 kroner",
     "marketscreener.com", "broker upgrade, aggregator"),
    (True, "Sandvik stock climbs after SEB rating upgrade and higher price target",
     "Ad-hoc-news.de", "same upgrade, weaker outlet"),
    (True, "Infineon acquires Bangalore-based C2i Semiconductors",
     "Evertiq", "acquisition, neutral trade press"),
    (True, "Yara issues profit warning on ammonia margins",
     "Ad-hoc-news.de", "profit warning outranks a weak publisher"),
    (True, "Equinor, Aker BP make gas find just northwest of Balder field",
     "Reuters", "no keyword, but a wire"),
    # And the other direction.
    (False, "Infineon acquires C2i Semiconductors", "gurufocus",
     "even a takeover does not clear a content farm"),
    (False, "ASML announces partnership with local supplier", "Ad-hoc-news.de",
     "a minor event from a weak outlet is not news"),
    (False, "Volvo shares in focus as investors weigh the quarter", "Electronics Weekly",
     "no event named and no wire behind it"),
    (False, "Infineon's Stock Trades at a 39% Discount to Its High", "Reuters",
     "junk framing fails even from a wire"),
]


# (headline, locale it was served from, expected language, description)
LANGUAGE_CASES = [
    # Google's locale says where a story was served, not what it is written in.
    ("Oljetoppens drøm: – Et nytt Castberg, et nytt Sverdrup", "da", "no",
     "Norwegian from the Danish feed, and no function word to go on"),
    ("Ny oljeallianse: Skal jakte storfunn på norsk sokkel", "da", "no",
     "likewise - the tell is inside a compound"),
    ("Aker BP-sjefen: – Dette koster oss 250 millioner dollar i året", "no", "no",
     "plainly Norwegian"),
    ("Novo Nordisk hæver forventningerne til året", "da", "da",
     "plainly Danish"),
    ("Mærsk sælger sin andel af virksomheden", "da", "da",
     "Danish vocabulary, not Norwegian"),
    ("Embracer sänker ordförandearvodet", "sv", "sv", "Swedish"),
    ("SAP Aktie: Kartellamt stellt Vorermittlungen ein", "de", "de", "German"),
    ("ASML boekt recordorders in het tweede kwartaal", "nl", "nl", "Dutch"),
    ("Airbus signe un contrat avec Lufthansa", "fr", "fr", "French"),
    ("Nokia sai suuren tilauksen Intiasta", "fi", "fi", "Finnish"),
    ("US Army orders second tranche of UH-72Bs", "en", "en", "English"),
]

# (headline, served locale, publisher, expected language, description)
# Who published it beats anything the headline says, and settles the Norwegian
# and Danish pair that word markers struggle with.
PUBLISHER_CASES = [
    ("Full drift ga resultatløft: – Et sterkt operasjonelt kvartal", "da", "E24",
     "no", "no vocabulary tell, but E24 is Norwegian"),
    ("Rykter om milliardordre fra Kristian Siem", "da", "Finansavisen", "no",
     "likewise"),
    ("Novo Nordisk hæver forventningerne", "no", "Borsen.dk", "da",
     "and the same in the other direction"),
    ("Embracer sänker ordförandearvodet", "da", "Di.se", "sv", "Swedish outlet"),
    ("Infineon hebt Prognose an", "en", "Handelsblatt", "de", "German outlet"),
    ("Castberg Sverdrup 2026", "da", "Unknown Outlet", "da",
     "nothing to go on at all: fall back to the feed"),
    # A Nordic outlet writing in English. The publisher must not override the
    # words, or MedWatch files its English as Danish.
    ("ALK CFO to receive DKK 25m payout under sign-on agreement", "da",
     "medwatch.com", "en", "Danish outlet, English article"),
    ("Novo Nordisk's acquisition spree marred by several failed deals", "da",
     "medwatch.com", "en", "same, and the publisher is Danish"),
    ("SB1 Markets reiterates buy on Ellos after earnings report", "sv",
     "marketscreener.com", "en", "English from a Swedish-served feed"),
    # " on " is the Finnish "is" and an English preposition. Scoring it as
    # Finnish sent English headlines to the translator as Finnish.
    ("Siemens Energy CEO Sees Data Center Boom Lasting on Power Needs", "en",
     "EnergyNow.com", "en", "English 'on' must not read as Finnish"),
    ("Cadeler H1 profit declines on year-ago one-off fees", "no",
     "Renewables Now", "en", "likewise"),
    # Norwegian and Danish, separated by vocabulary rather than grammar.
    ("(+) Salmars resultat svakere enn ventet", "da", "Kyst.no", "no",
     "svakere and enn are Norwegian; svagere and end are Danish"),
    ("Tryg frykter sparkesykkelulykker i høst", "da", "finanswatch.no", "no",
     "frykter, not frygter"),
    ("Advarer mot å sende barna til skolen på elsparkesykkel", "da",
     "Groruddalen", "no", "the bare infinitive marker å is Norwegian"),
    ("Mærsk sælger sin andel af virksomheden", "no", "", "da",
     "and virksomhed is Danish"),
    ("ASML boekt recordorders in het tweede kwartaal", "nl", "", "nl",
     "a genuine tie, settled by the feed it came from"),
    # Swedish against the other two. Spelling settles it: Swedish writes
    # a-diaeresis and o-diaeresis where Norwegian and Danish write ae and
    # o-slash. " mot " does not settle it - Swedish uses that word too, which
    # is how a Swedish railway story came out Norwegian.
    ("AI testas mot viltolyckor på järnvägen", "no", "", "sv",
     "Swedish, and the only clue is a letter"),
    ("Lars Wingefors sänker sitt ordförandearvode", "no", "", "sv",
     "likewise"),
    ("Oljetoppens drøm: – Et nytt Castberg", "sv", "", "no",
     "and the reverse: o-slash rules Swedish out"),
    # These isolate the spelling rule. No word in either is on any vocabulary
    # list, so only the letters can decide - without them both fall through to
    # whichever feed happened to serve the story.
    ("Ökade intäkter för Mycronic i kvartalet", "no", "", "sv",
     "Swedish by its letters alone"),
    ("Større omsætning i selskabets nordiske forretning", "sv", "", "da",
     "and ae/o-slash rule Swedish out, by letters alone"),
]

# (should_read, should_alert, headline, publisher, description)
READING_CASES = [
    # The page and the notification are not the same audience.
    (True, True, "Infineon acquires Bangalore-based C2i Semiconductors", "Evertiq",
     "an acquisition belongs in both"),
    # A top newsroom writing about the company at all clears the bar even with
    # no keyword in the headline. That rule is what caught Reuters on the Balder
    # gas find, which also named no event the vocabulary knows. The cost is
    # stories like this one; the alternative is missing the discovery.
    (True, True, "Aker BP opens new office in Stavanger", "E24",
     "top-tier source with no keyword still alerts, by design"),
    (False, False, "Sandvik opens new office in Stavanger", "Mining Technology",
     "the same non-event from an unweighted outlet does not even get read"),
    # The cases that actually separate the two gates. Without these, collapsing
    # worth_reading into worth_alerting passes the whole suite.
    (True, False, "Sandvik announces partnership with local supplier",
     "Mining Technology", "a minor event: read it on the page, do not buzz"),
    (True, False, "Yara launches new fertiliser range in Brazil", "Agg-Net",
     "likewise - a launch from an unweighted outlet is coverage, not an event"),
    (True, True, "Yara issues profit warning on ammonia margins", "Offshore Energy",
     "same outlet, real event: both gates open"),
    (False, False, "KOMMENTAR: HYDRO, YARA OG LAKSEAKSJER LØFTET OSLO BØRS FREDAG",
     "E24", "a daily index column is filler in any language"),
    (False, False, "Infineon's Stock Trades at a 39% Discount to Its High",
     "Electronics Weekly", "valuation arithmetic is filler too"),
]


# (raw from the translation service, what a reader must see, description)
# The page escapes on the way out, so anything still escaped here is shown
# literally: "Now they don&#39;t call" appeared on the live site.
TRANSLATION_CASES = [
    ("Equinor CEO Anders Opedal: – Now they don&#39;t call",
     "Equinor CEO Anders Opedal: – Now they don't call", "numeric entity"),
    ("Equinor&#39;s group shop steward on management",
     "Equinor's group shop steward on management", "possessive"),
    ("Infineon &amp; Bosch sign deal", "Infineon & Bosch sign deal", "ampersand"),
    ("  Yara halts production  ", "Yara halts production", "surrounding space"),
    ("Nothing to unescape here", "Nothing to unescape here", "left alone"),
]


def translation_budget() -> list[str]:
    """A limited allowance must be spread across languages, and must not be
    spent on headlines that could never be shown.

    The allowance is monthly. Grouping by language and working through one at a
    time means whichever language happens to be first takes the lot, and the
    rest of the world goes untranslated all month. And a headline from a
    content farm can never clear worth_reading whatever it says, so paying to
    translate it is paying to learn nothing.
    """
    import translate
    problems = []

    class Fake:
        name, batch, per_run = "fake", 2, 6

        def __init__(self):
            self.seen = []

        def translate(self, texts, lang):
            self.seen.extend((t, lang) for t in texts)
            return [f"EN({t})" for t in texts]

    translator = translate.Translator.__new__(translate.Translator)
    translator.cache, translator.hits = {}, 0
    translator.bought, translator.failures = 0, 0
    fake = Fake()
    translator.providers = [fake]
    translator.spent = {"fake": 0}
    translator.warm([(f"de{i}", "de") for i in range(6)]
                    + [(f"fr{i}", "fr") for i in range(6)]
                    + [(f"it{i}", "it") for i in range(6)])
    spread = {}
    for _, lang in fake.seen:
        spread[lang] = spread.get(lang, 0) + 1
    if len(spread) < 3:
        problems.append(
            f"a budget of 6 across three languages reached only {sorted(spread)} - "
            f"one language is taking the whole allowance")

    for publisher, title, want, why in (
        ("Reuters", "Yara halts ammonia production", True, "a wire is worth paying for"),
        ("Electronics Weekly", "Infineon wins design order", True, "so is a neutral outlet"),
        ("gurufocus", "Infineon acquires C2i", False,
         "a content farm can never clear worth_reading"),
        ("simplywall.st", "Yara: 5 Things You Need To Know", False, "likewise"),
        ("Reuters", "Infineon's Stock Trades at a 39% Discount", False,
         "junk framing is filler in any language"),
    ):
        got = worth_translating({"title": title, "publisher": publisher})
        if got != want:
            problems.append(f"worth_translating({publisher}) gave {got}, wanted {want} - {why}")
    return problems


def short_register_matching() -> list[str]:
    """A company must not be given another company's short interest.

    Token overlap is far too loose for this: "Andfjord Salmon" and "Salmon
    Evolution" share the word for what they farm, not for who they are, and the
    first version of this reported one company's disclosed position under the
    other's name - with a real number, a real date, and a real source, which is
    exactly what makes it dangerous.
    """
    register = {
        "salmon evolution": {"issuer": "SALMON EVOLUTION ASA", "percent": 2.58},
        "yara international": {"issuer": "YARA INTERNATIONAL", "percent": 0.51},
        "aker bp": {"issuer": "AKER BP", "percent": 0.71},
        "proximar seafood": {"issuer": "PROXIMAR SEAFOOD", "percent": 2.26},
    }
    cases = [
        ("Salmon Evolution", "SALMON EVOLUTION ASA", "exact"),
        ("Yara", "YARA INTERNATIONAL", "a leading phrase may be extended"),
        ("Aker BP", "AKER BP", "exact, two words"),
        ("Andfjord Salmon", None, "shares only the industry word"),
        ("Austevoll Seafood", None, "likewise"),
        ("Nordic Halibut", None, "no entry at all"),
        ("Evolution", None, "a trailing word is not a leading phrase"),
    ]
    problems = []
    for name, want, why in cases:
        got = match_short(name, register)
        issuer = got["issuer"] if got else None
        if issuer != want:
            problems.append(
                f"match_short({name!r}) gave {issuer!r}, wanted {want!r} - {why}")
    return problems


def batch_pairing() -> list[str]:
    """A batching provider must never mis-pair a translation to a headline.

    Both keyed providers send forty headlines in one request and match the
    replies back by position. If a service returns a short list - a partial
    failure, a filtered item, a truncated response - then zipping the two
    together silently attaches each translation to the wrong headline, and the
    result is cached under the wrong key and shown as though it were right.
    That is worse than no translation at all, and invisible.
    """
    import translate

    problems = []
    sent = ["eins", "zwei", "drei"]

    for name, provider, short, full in (
        ("deepl", DeepL("k:fx"),
         {"translations": [{"text": "one"}, {"text": "two"}]},
         {"translations": [{"text": "one"}, {"text": "two"}, {"text": "three"}]}),
        ("azure", Azure("k"),
         [{"translations": [{"text": "one"}]}],
         [{"translations": [{"text": "one"}]}, {"translations": [{"text": "two"}]},
          {"translations": [{"text": "three"}]}]),
    ):
        original = translate._post
        try:
            translate._post = lambda *a, **k: short
            got = provider.translate(sent, "de")
            if any(g is not None for g in got):
                problems.append(
                    f"{name}: a short reply produced {got} instead of discarding "
                    f"the batch - translations would be mis-paired")
            translate._post = lambda *a, **k: full
            got = provider.translate(sent, "de")
            if got != ["one", "two", "three"]:
                problems.append(f"{name}: a complete reply returned {got}")
        finally:
            translate._post = original
    return problems


def unpersisted_state() -> list[str]:
    """Files the scan must carry between runs but git would throw away.

    The runner is rebuilt for every scan, so anything not committed starts
    empty. data/seen.json was ignored, which meant every story was new on every
    run - nineteen alerts, nineteen of them "new", twelve times a day. On the
    page that only lights a marker; wired to a notification it is a pager going
    off hourly with the same news.
    """
    root = Path(__file__).resolve().parent.parent
    ignore = root / ".gitignore"
    patterns = ([l.strip() for l in ignore.read_text(encoding="utf-8").splitlines()]
                if ignore.exists() else [])
    must_persist = ("data/seen.json", "data/translations.json", "data/signals.json")
    return [name for name in must_persist
            if name in patterns or name.split("/")[-1] in patterns]


def stdlib_shadowing() -> list[str]:
    """Module names in scripts/ that the standard library already owns.

    A file called select.py here shadowed the stdlib select module, which socket
    and urllib import. Nothing referenced it - it was enough that it sat in a
    directory on sys.path. Every scheduled run failed at import for eight hours
    while the tests passed locally, because on Windows the modules it breaks had
    already been imported before the path was extended.
    """
    scripts = Path(__file__).resolve().parent.parent / "scripts"
    return sorted(
        path.stem for path in scripts.glob("*.py")
        if path.stem in sys.stdlib_module_names
    )


def main() -> int:
    failures = []

    for raw, want, label in TRANSLATION_CASES:
        got = clean(raw)
        if got != want:
            failures.append(f"clean: wanted {want!r}, got {got!r} - {label}")

    failures.extend(translation_budget())
    failures.extend(short_register_matching())
    failures.extend(batch_pairing())

    for name in unpersisted_state():
        failures.append(
            f"{name} is gitignored, but the scan needs it between runs - "
            f"the runner starts empty, so its state resets every hour")

    for name in stdlib_shadowing():
        failures.append(
            f"scripts/{name}.py shadows the standard library module '{name}' - "
            f"rename it, or anything importing '{name}' gets this file instead")

    for title, served, want, label in LANGUAGE_CASES:
        got = detect_language(title, served)
        if got != want:
            failures.append(
                f"detect_language: wanted {want}, got {got} (served {served}) - {label}")

    for title, served, publisher, want, label in PUBLISHER_CASES:
        got = detect_language(title, served, publisher)
        if got != want:
            failures.append(
                f"detect_language: wanted {want}, got {got} "
                f"(served {served}, {publisher}) - {label}")

    for read, alert, title, publisher, label in READING_CASES:
        item = {"material": _material(title), "sourceWeight": _source_weight(publisher),
                "junk": _news_score(title, publisher) == -5}
        if worth_reading(item) != read:
            failures.append(f"worth_reading: wanted {read} - {label} [{publisher}]")
        if worth_alerting(item) != alert:
            failures.append(f"worth_alerting: wanted {alert} - {label} [{publisher}]")

    for want, title, publisher, label in ALERT_CASES:
        item = {"material": _material(title), "sourceWeight": _source_weight(publisher),
                "junk": _news_score(title, publisher) == -5}
        got = worth_alerting(item)
        if got != want:
            failures.append(
                f"worth_alerting: wanted {want}, got {got} - {label} "
                f"(material={item['material']} source={item['sourceWeight']} "
                f"junk={item['junk']}) [{publisher}]"
            )

    for subject, a, b, want, label in STORY_CASES:
        got = same_story(a, [b], subject)
        if got != want:
            failures.append(
                f"same_story: wanted {want}, got {got} - {label}\n"
                f"    A distinctive: {sorted(distinctive(a, subject))}\n"
                f"    B distinctive: {sorted(distinctive(b, subject))}"
            )

    # Merging must not depend on which headline arrived first.
    for subject, a, b, want, label in STORY_CASES:
        if same_story(b, [a], subject) != want:
            failures.append(f"same_story not symmetric - {label}")

    for predicate, title, publisher, label in SCORE_CASES:
        score = _news_score(title, publisher)
        if not predicate(score):
            failures.append(f"_news_score: {score} fails its test - {label} [{publisher}]")

    total = (len(STORY_CASES) * 2 + len(SCORE_CASES) + len(ALERT_CASES)
             + len(LANGUAGE_CASES) + len(PUBLISHER_CASES)
             + len(READING_CASES) * 2 + len(TRANSLATION_CASES) + 19)
    if failures:
        print(f"FAIL  {len(failures)} of {total}\n")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"ok  {total} checks: {len(STORY_CASES)} story pairs (both directions), "
          f"{len(SCORE_CASES)} scores, {len(ALERT_CASES)} alert decisions, "
          f"{len(LANGUAGE_CASES) + len(PUBLISHER_CASES)} languages, "
          f"{len(READING_CASES)} read/alert splits, "
          f"no stdlib shadowing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
