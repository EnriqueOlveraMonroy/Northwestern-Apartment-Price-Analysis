"""
Parsea archivos HTML de Mercado Libre Inmuebles guardados manualmente
(Ctrl+S desde el navegador) y extrae los datos a un CSV.

Uso:
    1. Guarda las páginas de resultados en la carpeta html_pages/
       (ver instrucciones - Ctrl+S, "Página web, solo HTML")
    2. Corre: python parsear_paginas_guardadas.py
"""

import csv
import glob
import re

from bs4 import BeautifulSoup

CARPETA_HTML = "html_pages" # Cambia el nombre de la carpeta si quieres
OUTPUT_CSV = "departamentos_zona_metropolitana.csv"   # Cambia el nombre del archivo de salida si quieres


def clean_number(text: str) -> str:
    return re.sub(r"[^\d]", "", text or "")


def parse_card(card) -> dict | None:
    title_tag = card.select_one("a.poly-component__title") or card.select_one("h2 a")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)
    link = title_tag.get("href", "").split("#")[0]

    price_tag = card.select_one(".poly-price__current .andes-money-amount__fraction")
    price = clean_number(price_tag.get_text()) if price_tag else None

    currency_tag = card.select_one(".poly-price__current .andes-money-amount__currency-symbol")
    currency = currency_tag.get_text(strip=True) if currency_tag else "MXN"

    location_tag = card.select_one(".poly-component__location")
    location = location_tag.get_text(strip=True) if location_tag else None

    attrs_tags = card.select(".poly-attributes_list .poly-attributes_list__item")
    attrs_text = [t.get_text(strip=True) for t in attrs_tags]

    surface = next((a for a in attrs_text if "m²" in a), None)
    bedrooms = next((a for a in attrs_text if "recámara" in a or "recamara" in a), None)
    bathrooms = next((a for a in attrs_text if "baño" in a), None)

    img_tag = card.select_one("img")
    image_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else None

    return {
        "titulo": title,
        "precio": price,
        "moneda": currency,
        "ubicacion": location,
        "superficie": surface,
        "recamaras": bedrooms,
        "banos": bathrooms,
        "link": link,
        "imagen": image_url,
    }


def parse_all_files():
    archivos = sorted(glob.glob(f"{CARPETA_HTML}/*.html") + glob.glob(f"{CARPETA_HTML}/*.htm"))

    if not archivos:
        print(f"[!] No encontré archivos .html en la carpeta '{CARPETA_HTML}'.")
        print("    Revisa que la carpeta exista y tenga los archivos guardados.")
        return []

    print(f"[*] Encontré {len(archivos)} archivo(s) para procesar.\n")

    all_listings = []
    seen_links = set()

    for archivo in archivos:
        print(f"[*] Procesando {archivo}...")
        with open(archivo, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div.poly-card") or soup.select("li.ui-search-layout__item")

        if not cards:
            print(f"  [!] No encontré tarjetas en {archivo}. Puede que la estructura sea distinta.")
            continue

        nuevos = 0
        for card in cards:
            item = parse_card(card)
            if item and item["link"] not in seen_links:
                seen_links.add(item["link"])
                all_listings.append(item)
                nuevos += 1

        print(f"  [+] {nuevos} listados nuevos de este archivo (total: {len(all_listings)})")

    return all_listings


def save_to_csv(listings, filename):
    if not listings:
        print("\nNo se recolectó ningún listado.")
        return

    fieldnames = listings[0].keys()
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(listings)

    print(f"\n[✓] {len(listings)} listados guardados en {filename}")


if __name__ == "__main__":
    resultados = parse_all_files()
    save_to_csv(resultados, OUTPUT_CSV)
