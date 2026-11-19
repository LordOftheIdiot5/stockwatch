"""Versioned multi-label headline/form classification. No price or sentiment scoring."""
import re
VERSION=1
TOPICS={
 "numbers":r"\b(earnings|quarterly results|annual report|net profit|revenue|ebitda|ebit|gross margin|dividend|buyback|cash flow|resultat|omsetning|utbytte|vinst|omsattning|utdelning|quartalszahlen|gewinn|umsatz)\b",
 "prices":r"\b(alumini(?:um|m)|alumina|aluminiumpris(?:en|er)?|salmon prices?|laksepris(?:en|er)?|feed prices?|electricity prices?|power prices?|strompris(?:en|er)?|kraftpris(?:en|er)?|freight rates?|tanker rates?|charter rates?|oil prices?|oljepris(?:en|er)?|natural gas prices?|commodity prices?|interest rates?|rente(?:n|r)?|exchange rates?)\b",
 "operations":r"\b(production volumes?|production record|harvest volumes?|harvested|slaktevolum|produksjonsrekord|production outage|plant outage|capacity utilization|fleet deliveries|vessel deliveries|smelter shutdown|factory shutdown|manufacturing capacity|production ramp|operating update|trading update)\b",
 "potential":r"\b(new contracts?|contract award|contract awarded|signed (?:a |an )?(?:contract|agreement)|supply agreement|order backlog|new orders|new project|expansion plans?|investment plans?|product launch|guidance|outlook|profit warning|oppkjop|fusjon|kontrakt|avtale|prognos|resultatvarsel)\b",
 "risk":r"\b(export controls?|export restrictions?|sanctions?|lawsuit|regulatory investigation|antitrust|recall|cyberattack|bankruptcy|tax dispute|skattesak|sea lice|lakselus|mortality|supply disruption|debt covenant|profit warning|resultatvarsel|strike action|tariffs?|tollsatser)\b",
}
CATEGORY_MAP={"Earnings / results":"numbers","Dividends":"numbers","Capital & ownership":"numbers","M&A":"potential","Guidance":"potential","Contracts":"potential"}
def classify(item,text):
    """Only classify relevant records. Attention is the complete relevant feed,
    deliberately not a topic or a hype/sentiment label."""
    if item.get("relevance") not in ("strong","mentioned"):
        return []
    reasons={}
    form=item.get("form")
    if item.get("sourceFeed")=="sec_edgar" and item.get("match")=="issuer_code":
        # 8-K and 6-K are heterogeneous; their generic titles give no topic.
        if isinstance(form,str) and form.removesuffix("/A") in ("10-K","10-Q","20-F","40-F"):
            reasons["numbers"]="periodic SEC report"
    # Existing topic classification is less specific than a filing form. Keep
    # its category provenance, never imply that a headline is a verified fact.
    category=item.get("category")
    if category in CATEGORY_MAP:
        reasons.setdefault(CATEGORY_MAP[category],"headline category: "+category)
    for name,expression in TOPICS.items():
        match=re.search(expression,text,re.I)
        if match:reasons.setdefault(name,"headline phrase: "+match.group(0))
    return [{"driver":name,"basis":basis} for name,basis in sorted(reasons.items())]
