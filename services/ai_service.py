import os
from openai import OpenAI
import json

DISCLAIMER = "\n\nHinweis: Dies ist keine Anlageberatung, sondern eine allgemeine, KI-gestützte Informationszusammenfassung."

def fallback_analysis(ticker: str, name: str, buy_price: float | None, current_price: float | None) -> tuple[str, int]:
    perf = ""
    risk = 50
    if buy_price and current_price:
        pct = (current_price / buy_price - 1) * 100
        perf = f"\n\nPerformance seit Kaufpreis: ca. {pct:.1f} %. Kaufpreis: {buy_price:.2f}, aktueller Preis: {current_price:.2f}."
        risk = 65 if pct > 30 or pct < -25 else 50
    text = f"""Analyse für {name or ticker}

Chancen:
- Die Position kann langfristig interessant sein, wenn Umsatz, Gewinn und Cashflow stabil wachsen.
- Ein klarer Wettbewerbsvorteil und solide Bilanz würden die Investmentthese stärken.

Risiken:
- Prüfe Bewertung, Verschuldung, Margenentwicklung und aktuelle Nachrichten.
- Einzelaktien können stark schwanken; eine zu hohe Depotgewichtung erhöht das Risiko.

Offene Fragen:
- Warum hältst du diese Aktie?
- Wie hoch ist die Position relativ zum Gesamtdepot?
- Was wäre ein Grund zu verkaufen oder nachzukaufen?{perf}

Vorläufiges Fazit:
Die Aktie sollte anhand von Bewertung, Qualität, Wachstum und Nachrichten geprüft werden. Ohne weitere Fundamentaldaten ist keine klare Aussage möglich."""
    return text + DISCLAIMER, risk

def create_ai_analysis(ticker: str, name: str = "", quantity: float | None = None, buy_price: float | None = None, current_price: float | None = None) -> tuple[str, int]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_analysis(ticker, name, buy_price, current_price)

    client = OpenAI(api_key=api_key)
    prompt = f"""
Erstelle eine kurze, vorsichtige Aktienanalyse auf Deutsch.
Keine Kauf-/Verkaufsempfehlung. Keine Anlageberatung.
Struktur: Chancen, Risiken, Bewertung/Einordnung, offene Fragen, Fazit.
Ticker: {ticker}
Name: {name}
Stückzahl: {quantity}
Kaufpreis: {buy_price}
Aktueller Preis: {current_price}
Gib zusätzlich einen Risiko-Score von 0 bis 100 als letzte Zeile im Format: RISK_SCORE: 55
"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    text = response.choices[0].message.content or ""
    risk = 50
    for line in text.splitlines():
        if line.strip().startswith("RISK_SCORE:"):
            try:
                risk = int(line.split(":", 1)[1].strip())
                text = text.replace(line, "").strip()
            except ValueError:
                pass
    return text + DISCLAIMER, max(0, min(100, risk))
    
import re

def create_fundamental_analysis(
    ticker: str,
    name: str = "",
    price_data: dict | None = None,
    fundamentals: dict | None = None,
    performance: dict | None = None,
) -> tuple[str, int]:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        text = f"""Fundamentale Analyse für {name or ticker}

Für eine tiefere Fundamentalanalyse wird ein OpenAI API-Key benötigt.

Verfügbare Daten:
- Preis: {price_data}
- Fundamentaldaten: {fundamentals}
- Performance: {performance}
"""
        return text + DISCLAIMER, 50

    client = OpenAI(api_key=api_key)
    fundamentals_text = format_fundamentals_for_prompt(fundamentals)

    prompt = f"""
Erstelle eine konkrete fundamentale Aktienanalyse auf Deutsch.

Wichtig:
- Keine Anlageberatung.
- Keine direkte Kauf- oder Verkaufsempfehlung.
- Formuliere wie ein vorsichtiger Analyst.
- Analysiere die Investment-These, nicht nur die Kennzahlen.
- Vermeide generische Aussagen wie „gutes Wachstum“ oder „starke Marktposition“, wenn du sie nicht mit Geschäftsmodell, Kennzahlen oder Branchenlogik begründest.
- Jede Chance und jedes Risiko muss konkret zum Unternehmen passen.
- Wenn Daten fehlen, klar sagen, welche Aussage dadurch unsicher bleibt.
- Verwende Markdown mit ## Überschriften.
- Keine unnötigen Leerzeilen.
- Maximal 3–5 Sätze pro Abschnitt.

Aktie:
Ticker: {ticker}
Name: {name}

Aktueller Preis:
{price_data}

Fundamentaldaten und Unternehmensprofil:
{fundamentals_text}

Kursentwicklung:
{performance}

Struktur:

## Kurzfazit
Bewerte in wenigen Sätzen, ob das Unternehmen fundamental solide, wachstumsstark, defensiv, teuer, zyklisch oder riskant wirkt.

## Geschäftsmodell & Investment-These
Erkläre konkret:
- Was macht das Unternehmen?
- Womit verdient es Geld?
- Welche Produkte, Segmente oder Kundengruppen sind wichtig?
- Warum könnte das Unternehmen langfristig profitieren oder unter Druck geraten?

## Bewertung
Ordne KGV, Marktkapitalisierung, EV/EBITDA, Kurs-Umsatz und Kurs-Buchwert ein, soweit vorhanden.
Bewerte, ob die Aktie eher teuer, moderat oder günstig wirkt und warum.

## Wachstum & Profitabilität
Nutze Umsatzwachstum, Gewinnentwicklung, Margen, ROE, ROA und Cashflow, soweit vorhanden.
Erkläre, ob Wachstum profitabel wirkt oder ob Warnsignale sichtbar sind.

## Bilanz, Cashflow & Dividende
Ordne Verschuldung, Free Cashflow, operativen Cashflow, Dividendenrendite und Ausschüttungsquote ein.

## Chancen
Nenne 3 konkrete Chancen, die zum Unternehmen passen.

## Risiken
Nenne 3 konkrete Risiken, die zum Unternehmen passen.

## Externe Einflussfaktoren
Erkläre passende Makro- oder Branchentreiber, z. B. Zinsen, Konjunktur, Rohstoffe, Energiepreise, KI, Halbleiter, Regulierung, geopolitische Risiken oder demografische Entwicklung.
Nenne nur Faktoren, die zum Unternehmen passen.

## Kurzfristige vs. langfristige Treiber
Was könnte den Kurs kurzfristig bewegen?
Was ist für die langfristige Entwicklung wichtiger?

## Offene Prüf-Punkte
- Nenne 5 konkrete Punkte, die man vor einer Entscheidung prüfen sollte.

## Fazit
Zusammenfassende Einschätzung in 3–5 Sätzen.

Gib zusätzlich einen Risiko-Score von 0 bis 100 als letzte Zeile im Format:
RISK_SCORE: 55
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
        )

        text = response.choices[0].message.content or ""
        text = re.sub(r"\n{3,}", "\n\n", text)

        risk = 50
        for line in text.splitlines():
            if line.strip().startswith("RISK_SCORE:"):
                try:
                    risk = int(line.split(":", 1)[1].strip())
                    text = text.replace(line, "").strip()
                except ValueError:
                    pass

        return text + DISCLAIMER, max(0, min(100, risk))

    except Exception as e:
        print(f"Fundamental analysis failed for {ticker}: {e}")
        return (
            "Die fundamentale Analyse konnte nicht erstellt werden."
            + DISCLAIMER,
            50,
        )


def fmt(value, suffix=""):
    if value is None:
        return "nicht verfügbar"
    try:
        if isinstance(value, (int, float)):
            return f"{value:,.2f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        pass
    return f"{value}{suffix}"


def format_fundamentals_for_prompt(fundamentals: dict | None) -> str:
    f = fundamentals or {}

    return f"""
Unternehmensprofil:
- Beschreibung: {f.get("business_summary") or "nicht verfügbar"}
- Website: {f.get("website") or "nicht verfügbar"}
- Land: {f.get("country") or "nicht verfügbar"}
- Mitarbeiter: {fmt(f.get("employees"))}
- Sektor: {f.get("sector") or "nicht verfügbar"}
- Branche: {f.get("industry") or "nicht verfügbar"}
- Währung: {f.get("currency") or "nicht verfügbar"}

Bewertung:
- Marktkapitalisierung: {fmt(f.get("market_cap"))}
- Enterprise Value: {fmt(f.get("enterprise_value"))}
- KGV trailing: {fmt(f.get("pe_ratio"))}
- KGV forward: {fmt(f.get("forward_pe"))}
- Kurs-Buchwert-Verhältnis: {fmt(f.get("price_to_book"))}
- Kurs-Umsatz-Verhältnis: {fmt(f.get("price_to_sales"))}
- EV/EBITDA: {fmt(f.get("ev_to_ebitda"))}

Wachstum:
- Umsatz: {fmt(f.get("revenue"))}
- Umsatzwachstum YoY: {fmt(f.get("revenue_growth_yoy"), " %")}
- Nettogewinn: {fmt(f.get("net_income"))}
- Gewinnwachstum YoY: {fmt(f.get("net_income_growth_yoy"), " %")}

Margen & Profitabilität:
- Bruttomarge: {fmt(f.get("gross_margin"), " %")}
- Operative Marge: {fmt(f.get("operating_margin"), " %")}
- Gewinnmarge: {fmt(f.get("profit_margin"), " %")}
- EBITDA-Marge: {fmt(f.get("ebitda_margin"), " %")}
- ROE: {fmt(f.get("roe"), " %")}
- ROA: {fmt(f.get("roa"), " %")}

Bilanz & Cashflow:
- Verschuldung zu Eigenkapital: {fmt(f.get("debt_to_equity"))}
- Gesamtverschuldung: {fmt(f.get("total_debt"))}
- Free Cashflow: {fmt(f.get("free_cashflow"))}
- Operativer Cashflow: {fmt(f.get("operating_cashflow"))}

Dividende:
- Dividendenrendite: {fmt(f.get("dividend_yield"), " %")}
- Ausschüttungsquote: {fmt(f.get("payout_ratio"), " %")}
"""

def create_investment_ideas(
    horizon: str,
    risk_level: str,
    goal: str,
    region: str,
    amount: float | None = None,
    exclusions: str | None = None,
    sector: str | None = None,
    market_cap: str | None = None,
    popularity: str | None = None,
) -> list[dict]:
    api_key = os.getenv("OPENAI_API_KEY")

    fallback = f"""Investment-Orientierung

Anlagehorizont: {horizon}
Risikoneigung: {risk_level}
Ziel: {goal}
Region: {region}

Mögliche Richtung:
- Breit gestreute ETFs können als Basisbaustein sinnvoll sein.
- Einzelaktien eher als Beimischung, wenn du höhere Schwankungen akzeptierst.
- Bei niedrigem Risiko eher globale Diversifikation, weniger Einzelwerte.
- Bei höherem Risiko können Wachstumsaktien oder Themen-ETFs geprüft werden.

Ausschlüsse:
{exclusions or "Keine angegeben"}

Hinweis: Dies ist keine Anlageberatung, sondern eine allgemeine Orientierung."""
    if not api_key:
        return fallback, 50

    client = OpenAI(api_key=api_key)

    prompt = f"""
    Erstelle konkrete Investment-Ideen auf Deutsch.

    Rahmen:
    - Anlagehorizont: {horizon}
    - Risiko: {risk_level}
    - Ziel: {goal}
    - Region: {region}
    - Budget: {amount}
    - Ausschlüsse: {exclusions}
    - Gewünschter Sektor: {sector or "egal"}
    - Marktkapitalisierung: {market_cap or "egal"}
    - Bekanntheitsgrad: {popularity or "gemischt"}

    Aufgabe:
    Gib GENAU 3 bis 5 konkrete Aktienideen zurück.
    
    WICHTIG:
    - Vermeide immer nur Standardnamen wie Tesla, Nvidia, Apple, Microsoft, ASML.
    - Wenn "weniger bekannte Aktien" gewählt ist, nenne solide, aber nicht extrem gehypte Unternehmen.
    - Wenn Small/Mid Cap gewählt ist, keine Mega Caps nennen.
    - Wenn niedriges Risiko gewählt ist, bevorzuge profitable, etablierte Unternehmen.
    - Wenn hohes Risiko gewählt ist, darfst du wachstumsstärkere, volatilere Aktien nennen.
    - Berücksichtige Sektor, Region, Stil und Marktkapitalisierung konsequent.
    - Keine Kaufempfehlung, sondern Kandidaten zur weiteren Prüfung.

    Für jede Aktie:
    - Ticker
    - Name
    - Kurze Begründung (2–4 Sätze)
    - Chancen
    - Risiken

    Format (WICHTIG – JSON!):

    [
      {{
        "ticker": "AAPL",
        "name": "Apple",
        "sector": "Technologie",
        "market_cap_category": "Mega Cap",
        "reason": "...",
        "chances": "...",
        "risks": "...",
        "risk_score": 40
      }}
    ]

    Gib ausschließlich valides JSON zurück. Keine Markdown-Codeblöcke, keine ```json-Markierung, kein zusätzlicher Text.
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    text = response.choices[0].message.content or ""

    # Markdown-Codeblock entfernen, falls Modell ```json ... ``` zurückgibt
    clean_text = text.strip()

    if clean_text.startswith("```json"):
        clean_text = clean_text.removeprefix("```json").strip()

    if clean_text.startswith("```"):
        clean_text = clean_text.removeprefix("```").strip()

    if clean_text.endswith("```"):
        clean_text = clean_text.removesuffix("```").strip()

    try:
        ideas = json.loads(clean_text)
    except Exception as e:
        print("JSON parsing failed:", e)
        print("Raw model output:", text)
        return [{
            "ticker": "ERROR",
            "name": "Parsing fehlgeschlagen",
            "reason": text,
            "chances": "",
            "risks": "",
            "risk_score": 50
        }]

    return ideas
    
def create_news_analysis(ticker: str, name: str, news: list[dict]) -> tuple[str, int]:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or not news:
        return "Keine aktuellen News verfügbar." + DISCLAIMER, 50

    client = OpenAI(api_key=api_key)

    news_text = "\n\n".join([
        f"- {n.get('title')}\n{n.get('summary')}"
        for n in news[:8]
        if n.get("title")
    ])
    print("NEWS RAW:", news)
    print("NEWS TEXT:", news_text)

    prompt = f"""
Analysiere die aktuellen Nachrichten zu einer Aktie.

Aktie: {name} ({ticker})

News:
{news_text}

Aufgabe:
Erstelle eine kompakte Analyse:

1. Kurzüberblick
2. Wichtige Themen/Trends
3. Positive Signale
4. Negative Risiken
5. Mögliche Auswirkungen auf den Kurs (kurzfristig vs langfristig)

Wichtig:
- Analysiere ob es ein erhöhtes Nachrichtenvolumen zu der Aktie gibt
- In welchem Marktumfeld wird die Aktie erwähnt
- Handelt es sich um seriöse Medien (Überregionale Zeitungen, Medien) oder eher um kleine Onlinemedien


"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        text = response.choices[0].message.content or ""
        text = text.replace("\n\n\n", "\n\n")

        risk = 50
        for line in text.splitlines():
            if line.strip().startswith("RISK_SCORE:"):
                try:
                    risk = int(line.split(":")[1].strip())
                    text = text.replace(line, "").strip()
                except:
                    pass

        return text + DISCLAIMER, risk

    except Exception as e:
        print(f"News analysis failed: {e}")
        return "News-Analyse konnte nicht erstellt werden." + DISCLAIMER, 50