#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skrypt naprawiający problemy SEO dla Etsy na podstawie analizy eRank.

Naprawia:
1. Tytuły - główne słowo kluczowe na początku, usunięcie powtórzeń
2. Opisy - słowa kluczowe w pierwszych 160 znakach, usunięcie pytajników i emoji z początku
3. Tagi - zamiana jednowyrazowych na frazy wielowyrazowe

Autor: Claude Code
Data: 2026-01-31
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple
import unicodedata


# ============================================================================
# KONFIGURACJA
# ============================================================================

INPUT_TITLES_FILE = "etsy_seo_titles_descriptions.csv"
INPUT_TAGS_FILE = "etsy_tags.csv"
OUTPUT_TITLES_FILE = "etsy_seo_titles_descriptions_FIXED.csv"
OUTPUT_TAGS_FILE = "etsy_tags_FIXED.csv"
REPORT_FILE = "etsy_seo_fix_report.md"

# Maksymalna długość tytułu Etsy
MAX_TITLE_LENGTH = 140

# Słowa kluczowe które powinny być na początku (w kolejności priorytetów)
PRIORITY_KEYWORDS = [
    "Polymer Clay Earrings",
    "Polymer Clay Studs",
    "Polymer Clay Dangle",
    "Clay Earrings",
]

# Tagi jednowyrazowe do zamiany na frazy
SINGLE_WORD_TAG_FIXES = {
    "hypoallergenic": "hypoallergenic earrings",
    "lightweight": "lightweight earrings",
    "handmade": "handmade jewelry",
    "botanical": "botanical jewelry",
    "minimalist": "minimalist style",
    "romantic": "romantic jewelry",
    "elegant": "elegant jewelry",
    "vintage": "vintage style",
    "boho": "boho style",
    "kawaii": "kawaii jewelry",
    "cottagecore": "cottagecore style",
    "coquette": "coquette aesthetic",
    "trendy": "trendy jewelry",
}

# Emoji do usunięcia z początku opisu
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"
    "\u3030"
    "]+",
    flags=re.UNICODE
)


# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def remove_leading_emoji(text: str) -> str:
    """Usuwa emoji z początku tekstu (pierwsze 50 znaków)."""
    # Znajdź pierwszy znaczący tekst (nie emoji, nie whitespace)
    lines = text.split('\n')
    new_lines = []
    found_text = False

    for line in lines:
        stripped = line.strip()
        # Usuń emoji z linii
        cleaned = EMOJI_PATTERN.sub('', stripped).strip()

        # Pomiń puste linie na początku
        if not found_text and not cleaned:
            continue

        # Pomiń linie które są tylko emoji
        if not found_text and len(stripped) > 0 and len(cleaned) == 0:
            continue

        found_text = True
        new_lines.append(line)

    return '\n'.join(new_lines)


def fix_description_start(description: str, product_name: str, style: str, colors: str) -> str:
    """
    Naprawia początek opisu - umieszcza słowa kluczowe w pierwszych 160 znakach.
    Usuwa emoji z początku i zamienia pytajniki na twierdzenia.
    """
    # Wyodrębnij sekcję kolorów z oryginalnego opisu
    colors_match = re.search(r'★ COLORS?:\s*([^\n★]+)', description)
    if colors_match:
        colors = colors_match.group(1).strip()

    # Nowy początek opisu (SEO-friendly, bez emoji, bez pytajników)
    # Pierwsze 160 znaków musi zawierać główne słowa kluczowe

    new_intro = f"""Handmade {product_name.lower()} crafted with premium polymer clay in Poland. These beautiful {style} earrings feature {colors.lower()} tones and hypoallergenic surgical steel hooks. Perfect unique gift for her - ships within 24-48h across EU!

WHY YOU'LL LOVE THESE:
- Unique handmade design - no two pairs are exactly alike
- Ultra-lightweight (3-5g per pair) - comfortable all day wear
- Hypoallergenic surgical steel hooks - safe for sensitive ears
- Made with premium polymer clay
- Ships from EU - fast delivery across Europe"""

    # Znajdź pozostałą część opisu (od COLORS do końca, ale bez pierwszych sekcji)
    rest_match = re.search(r'(★ COLORS?:.*)', description, re.DOTALL)
    if rest_match:
        rest = rest_match.group(1)
        # Usuń sekcję WHY YOU'LL LOVE THESE jeśli jest w rest
        rest = re.sub(r'★ WHY YOU\'?LL LOVE THESE?:.*?(?=★|$)', '', rest, flags=re.DOTALL)
        # Wyczyść podwójne gwiazdki
        rest = re.sub(r'\n\n+', '\n\n', rest)
    else:
        rest = ""

    # Złóż nowy opis
    full_description = new_intro + "\n\n" + rest.strip()

    # Usuń linię z hashtagami na końcu (ta z kropkami •)
    full_description = re.sub(r'\n─+\n.*?•.*$', '', full_description, flags=re.MULTILINE)

    # Wyczyść wielokrotne puste linie
    full_description = re.sub(r'\n{3,}', '\n\n', full_description)

    return full_description.strip()


def extract_product_info(title: str) -> Tuple[str, str, str]:
    """Wyodrębnia nazwę produktu, styl i kolory z tytułu."""
    # Usuń "Polymer Clay" i "Earrings" żeby dostać rdzeń nazwy
    parts = [p.strip() for p in title.split(',')]

    product_name = parts[0] if parts else title

    # Wykryj styl
    style_keywords = {
        'boho': 'boho',
        'minimalist': 'minimalist',
        'elegant': 'elegant',
        'vintage': 'vintage',
        'retro': 'retro',
        'romantic': 'romantic',
        'cute': 'cute',
        'kawaii': 'kawaii',
        'botanical': 'botanical',
        'floral': 'floral',
        'modern': 'modern',
        'statement': 'statement',
        'glamour': 'glamorous',
        'bridal': 'bridal',
        'coquette': 'coquette',
    }

    style = 'unique'
    title_lower = title.lower()
    for keyword, style_name in style_keywords.items():
        if keyword in title_lower:
            style = style_name
            break

    # Wykryj kolory
    color_keywords = ['blue', 'red', 'pink', 'orange', 'green', 'yellow', 'purple',
                      'black', 'white', 'gold', 'silver', 'coral', 'burgundy',
                      'vanilla', 'beige', 'navy', 'turquoise', 'lilac', 'pastel']

    colors = []
    for color in color_keywords:
        if color in title_lower:
            colors.append(color.capitalize())

    colors_str = ', '.join(colors[:3]) if colors else 'mixed'

    return product_name, style, colors_str


def fix_title(old_title: str) -> str:
    """
    Naprawia tytuł:
    1. Umieszcza "Polymer Clay" na początku
    2. Usuwa powtórzenia słów
    3. Zachowuje czytelność
    4. Max 140 znaków
    """
    # Najpierw wyczyść tytuł z wszelkich wariantów "Clay Earrings" (bez Polymer)
    # żeby uniknąć "Polymer Clay Boho Clay Earrings"
    cleaned_title = old_title

    # Usuń samodzielne "Clay Earrings" (zostaw tylko jeśli jest "Polymer Clay")
    # Zamień "Boho Clay Earrings" na "Boho Earrings"
    cleaned_title = re.sub(r'\bClay\s+Earrings\b', 'Earrings', cleaned_title, flags=re.IGNORECASE)
    # Usuń samodzielne "Clay" które nie jest po "Polymer"
    cleaned_title = re.sub(r'(?<!\bPolymer\s)\bClay\b', '', cleaned_title, flags=re.IGNORECASE)
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()

    # Parsuj części tytułu
    parts = [p.strip() for p in cleaned_title.split(',')]

    # Sprawdź czy tytuł zaczyna się od polymer clay
    starts_with_polymer = cleaned_title.lower().startswith('polymer clay')

    if not starts_with_polymer:
        # Sprawdź czy "Polymer Clay" jest gdzieś w tytule
        polymer_in_title = 'polymer clay' in cleaned_title.lower()

        # Zbuduj nowy tytuł
        if polymer_in_title:
            # Usuń "Polymer Clay" z miejsca gdzie jest i dodaj na początek
            new_parts = []
            for part in parts:
                cleaned = re.sub(r'\bPolymer Clay\b', '', part, flags=re.IGNORECASE).strip()
                cleaned = re.sub(r'\s+', ' ', cleaned)  # Usuń podwójne spacje
                if cleaned and cleaned not in new_parts:
                    new_parts.append(cleaned)

            # Dodaj Polymer Clay na początek pierwszej części
            if new_parts:
                first_part = new_parts[0]
                # Sprawdź czy to studs, dangle lub earrings
                if 'stud' in first_part.lower() or 'dangle' in first_part.lower() or 'earring' in first_part.lower():
                    new_title = f"Polymer Clay {first_part}"
                else:
                    new_title = f"Polymer Clay {first_part} Earrings"

                # Dodaj pozostałe części (bez powtórzeń)
                seen_words = set(new_title.lower().split())
                for part in new_parts[1:]:
                    part_words = set(part.lower().split())
                    if part_words - seen_words:
                        new_title += f", {part}"
                        seen_words.update(part_words)
            else:
                new_title = f"Polymer Clay {cleaned_title}"
        else:
            # Brak polymer clay - dodaj na początek
            first_part = parts[0] if parts else cleaned_title
            if 'stud' in first_part.lower() or 'dangle' in first_part.lower() or 'earring' in first_part.lower():
                new_title = f"Polymer Clay {first_part}"
            else:
                new_title = f"Polymer Clay {first_part} Earrings"

            # Dodaj pozostałe części
            seen_words = set(new_title.lower().split())
            for part in parts[1:]:
                if part:
                    part_words = set(part.lower().split())
                    if part_words - seen_words:
                        new_title += f", {part}"
                        seen_words.update(part_words)
    else:
        new_title = cleaned_title

    # Usuń powtórzone słowa w tytule
    new_title = remove_duplicate_words_in_title(new_title)

    # Finalne czyszczenie
    new_title = re.sub(r'\s+', ' ', new_title)
    new_title = re.sub(r',\s*,', ',', new_title)  # Usuń podwójne przecinki

    # Ogranicz długość
    if len(new_title) > MAX_TITLE_LENGTH:
        truncated = new_title[:MAX_TITLE_LENGTH]
        last_comma = truncated.rfind(',')
        if last_comma > 50:
            new_title = truncated[:last_comma]
        else:
            new_title = truncated.rsplit(' ', 1)[0]

    return new_title.strip()


def remove_duplicate_words_in_title(title: str) -> str:
    """Usuwa powtórzone słowa zachowując strukturę tytułu."""
    parts = [p.strip() for p in title.split(',')]

    seen_significant_words = set()
    new_parts = []

    # Słowa które mogą się powtarzać (łączniki, przyimki)
    ignore_words = {'for', 'her', 'him', 'the', 'a', 'an', 'and', 'or', 'with', 'in', 'on', 'to', 'of'}

    for part in parts:
        words = part.split()
        significant_words = [w.lower() for w in words if w.lower() not in ignore_words and len(w) > 2]

        # Sprawdź czy ta część wnosi nowe słowa
        new_words = [w for w in significant_words if w not in seen_significant_words]

        if new_words or not significant_words:  # Zachowaj jeśli są nowe słowa lub to np. "Gift for Her"
            new_parts.append(part)
            seen_significant_words.update(significant_words)

    return ', '.join(new_parts)


def fix_tag(tag: str) -> str:
    """
    Naprawia pojedynczy tag:
    1. Zamienia jednowyrazowe na frazy
    2. Max 20 znaków
    """
    tag = tag.strip().lower()

    # Specjalna obsługa "polymer clay" - zawsze zamień na "polymer clay earrings"
    if tag == "polymer clay":
        return "polymer clay earrings"

    # Specjalna obsługa "polymer clay earrings" - zachowaj
    if tag == "polymer clay earrings":
        return tag

    # Sprawdź czy to tag jednowyrazowy do zamiany
    if tag in SINGLE_WORD_TAG_FIXES:
        tag = SINGLE_WORD_TAG_FIXES[tag]
    elif ' ' not in tag and len(tag) < 15:
        # Jednowyrazowy tag - spróbuj dodać "earrings" lub "jewelry"
        if tag.endswith('s'):
            # Już liczba mnoga - może to być ok
            pass
        elif tag in ['boho', 'kawaii', 'coquette', 'cottagecore']:
            tag = f"{tag} style"
        elif tag not in ['handmade', 'unique', 'artisan']:
            tag = f"{tag} earrings"

    # Ogranicz do 20 znaków
    if len(tag) > 20:
        # Spróbuj skrócić inteligentnie
        words = tag.split()
        if len(words) > 1:
            # Usuń ostatnie słowo jeśli to pomoże
            shortened = ' '.join(words[:-1])
            if len(shortened) <= 20:
                tag = shortened
            else:
                tag = tag[:20]
        else:
            tag = tag[:20]

    return tag


def fix_tags_list(tags: List[str]) -> List[str]:
    """Naprawia listę tagów."""
    fixed_tags = []
    seen_tags = set()

    for tag in tags:
        if not tag or not tag.strip():
            continue

        fixed = fix_tag(tag)

        # Unikaj duplikatów
        if fixed.lower() not in seen_tags:
            fixed_tags.append(fixed)
            seen_tags.add(fixed.lower())

    # Upewnij się że mamy core tags
    core_tags = [
        "polymer clay earrings",
        "handmade in poland",
        "gift for her",
    ]

    for core in core_tags:
        if core not in seen_tags and len(fixed_tags) < 13:
            fixed_tags.append(core)
            seen_tags.add(core)

    # Max 13 tagów
    return fixed_tags[:13]


def generate_new_description(old_description: str, title: str) -> str:
    """Generuje nowy opis z naprawionym początkiem."""
    product_name, style, colors = extract_product_info(title)
    return fix_description_start(old_description, product_name, style, colors)


# ============================================================================
# GŁÓWNE FUNKCJE PRZETWARZANIA
# ============================================================================

def process_titles_and_descriptions(input_file: Path, output_file: Path) -> List[Dict]:
    """Przetwarza plik z tytułami i opisami."""
    results = []

    with open(input_file, 'r', encoding='utf-8') as f:
        # Użyj średnika jako separatora
        reader = csv.DictReader(f, delimiter=';', quotechar='"')

        for row in reader:
            produkt_id = row.get('produkt_id', '')
            produkt_sku = row.get('produkt_sku', '')
            stary_tytul = row.get('stary_tytul', '')
            obecny_tytul = row.get('nowy_tytul_seo', '')
            obecny_opis = row.get('nowy_opis_seo', '')

            # Napraw tytuł
            nowy_tytul = fix_title(obecny_tytul)

            # Napraw opis
            nowy_opis = generate_new_description(obecny_opis, nowy_tytul)

            results.append({
                'produkt_id': produkt_id,
                'produkt_sku': produkt_sku,
                'stary_tytul': stary_tytul,
                'poprzedni_tytul_seo': obecny_tytul,
                'nowy_tytul_seo': nowy_tytul,
                'nowy_opis_seo': nowy_opis,
            })

    # Zapisz wyniki
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['produkt_id', 'produkt_sku', 'stary_tytul', 'poprzedni_tytul_seo', 'nowy_tytul_seo', 'nowy_opis_seo']
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(results)

    return results


def process_tags(input_file: Path, output_file: Path) -> List[Dict]:
    """Przetwarza plik z tagami."""
    results = []

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';', quotechar='"')

        for row in reader:
            produkt_id = row.get('produkt_id', '')
            produkt_sku = row.get('produkt_sku', '')
            tytul = row.get('tytul', '')

            # Zbierz wszystkie tagi
            old_tags = []
            for i in range(1, 14):
                tag = row.get(f'tag_{i}', '')
                if tag:
                    old_tags.append(tag)

            # Napraw tagi
            new_tags = fix_tags_list(old_tags)

            result = {
                'produkt_id': produkt_id,
                'produkt_sku': produkt_sku,
                'tytul': tytul,
            }

            # Dodaj naprawione tagi
            for i, tag in enumerate(new_tags, 1):
                result[f'tag_{i}'] = tag

            # Wypełnij puste tagi
            for i in range(len(new_tags) + 1, 14):
                result[f'tag_{i}'] = ''

            results.append(result)

    # Zapisz wyniki
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['produkt_id', 'produkt_sku', 'tytul'] + [f'tag_{i}' for i in range(1, 14)]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(results)

    return results


def generate_report(titles_results: List[Dict], tags_results: List[Dict], report_file: Path):
    """Generuje raport z wprowadzonych zmian."""

    report = f"""# Raport naprawy SEO Etsy
Data: 2026-01-31

## Podsumowanie

- **Przetworzono produktów (tytuły/opisy):** {len(titles_results)}
- **Przetworzono produktów (tagi):** {len(tags_results)}

## Wprowadzone zmiany

### 1. Tytuły
- Dodano "Polymer Clay" na początek każdego tytułu
- Usunięto powtórzone słowa
- Zachowano max 140 znaków

### 2. Opisy
- Usunięto emoji z początku opisu
- Zamieniono pytajniki na twierdzenia
- Umieszczono słowa kluczowe w pierwszych 160 znakach
- Zoptymalizowano strukturę opisu

### 3. Tagi
- Zamieniono tagi jednowyrazowe na frazy wielowyrazowe
- Dodano core tags: "polymer clay earrings", "handmade in poland", "gift for her"
- Zachowano max 13 tagów po max 20 znaków

## Przykłady zmian w tytułach

| SKU | Przed | Po |
|-----|-------|-----|
"""

    # Dodaj przykłady (pierwsze 5)
    for result in titles_results[:5]:
        przed = result['poprzedni_tytul_seo'][:50] + '...' if len(result['poprzedni_tytul_seo']) > 50 else result['poprzedni_tytul_seo']
        po = result['nowy_tytul_seo'][:50] + '...' if len(result['nowy_tytul_seo']) > 50 else result['nowy_tytul_seo']
        report += f"| {result['produkt_sku']} | {przed} | {po} |\n"

    report += """

## Pliki wyjściowe

1. `etsy_seo_titles_descriptions_FIXED.csv` - naprawione tytuły i opisy
2. `etsy_tags_FIXED.csv` - naprawione tagi

## Następne kroki

1. ✅ Przejrzyj wygenerowane pliki
2. ⏳ Zaimportuj do BaseLinker/Etsy
3. ⏳ Uzupełnij Materials i Attributes w Etsy (ręcznie)
4. ⏳ Dodaj alt text do zdjęć (ręcznie)
5. ⏳ Nagraj i dodaj filmy produktowe
6. ⏳ Zweryfikuj ponownie w eRank
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Główna funkcja programu."""
    print("=" * 60)
    print("NAPRAWA SEO ETSY - eRank Optimization")
    print("=" * 60)
    print()

    # Ścieżki plików
    script_dir = Path(__file__).parent
    input_titles = script_dir / INPUT_TITLES_FILE
    input_tags = script_dir / INPUT_TAGS_FILE
    output_titles = script_dir / OUTPUT_TITLES_FILE
    output_tags = script_dir / OUTPUT_TAGS_FILE
    report = script_dir / REPORT_FILE

    # Sprawdź czy pliki istnieją
    if not input_titles.exists():
        print(f"❌ BŁĄD: Nie znaleziono pliku {INPUT_TITLES_FILE}")
        return

    if not input_tags.exists():
        print(f"❌ BŁĄD: Nie znaleziono pliku {INPUT_TAGS_FILE}")
        return

    print(f"📂 Przetwarzam tytuły i opisy z: {INPUT_TITLES_FILE}")
    titles_results = process_titles_and_descriptions(input_titles, output_titles)
    print(f"✅ Zapisano {len(titles_results)} produktów do: {OUTPUT_TITLES_FILE}")
    print()

    print(f"📂 Przetwarzam tagi z: {INPUT_TAGS_FILE}")
    tags_results = process_tags(input_tags, output_tags)
    print(f"✅ Zapisano {len(tags_results)} produktów do: {OUTPUT_TAGS_FILE}")
    print()

    print(f"📝 Generuję raport...")
    generate_report(titles_results, tags_results, report)
    print(f"✅ Raport zapisany do: {REPORT_FILE}")
    print()

    print("=" * 60)
    print("GOTOWE!")
    print("=" * 60)
    print()
    print("Następne kroki:")
    print("1. Przejrzyj pliki *_FIXED.csv")
    print("2. Zaimportuj do BaseLinker/Etsy")
    print("3. Uzupełnij Materials i Attributes w Etsy")
    print("4. Dodaj alt text do zdjęć")
    print("5. Nagraj filmy produktowe")
    print("6. Sprawdź ponownie w eRank")


if __name__ == "__main__":
    main()
