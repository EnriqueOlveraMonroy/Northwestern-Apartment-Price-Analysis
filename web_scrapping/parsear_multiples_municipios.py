"""
Parsea archivos HTML de Mercado Libre Inmuebles guardados manualmente,
organizados en subcarpetas por municipio, y genera un CSV por cada una.

Estructura esperada:

    html_pages/
        ATIZAPAN DE ZARAGOZA/
            pagina_01.html
            pagina_02.html
            ...
        AZCAPOTZALCO/
            pagina_01.html
            ...
        GUSTAVO A MADERO/
            ...
        NAUCALPAN/
            ...
        TLALNEPANTLA/
            ...

Uso:
    python parsear_multiples_municipios.py

Salida:
    - Un CSV por municipio, ej: departamentos_ATIZAPAN_DE_ZARAGOZA.csv
    - Un CSV combinado con todos los municipios: departamentos_TODOS.csv
"""

import csv
import glob
import os
import re

from bs4 import BeautifulSoup

CARPETA_RAIZ = "html_pages"     # carpeta que contiene las subcarpetas por municipio
CARPETA_SALIDA = "resultados"    # donde se guardan los CSVs generados


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


def parse_folder(carpeta: str) -> list[dict]:
    """Parsea todos los .html de una carpeta (un municipio) y regresa la lista de listados."""
    archivos = sorted(glob.glob(os.path.join(carpeta, "*.html")) + glob.glob(os.path.join(carpeta, "*.htm")))

    if not archivos:
        print(f"  [!] No encontré archivos .html en '{carpeta}'.")
        return []

    listings = []
    seen_links = set()

    for archivo in archivos:
        with open(archivo, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div.poly-card") or soup.select("li.ui-search-layout__item")

        if not cards:
            print(f"  [!] No encontré tarjetas en {archivo}.")
            continue

        nuevos = 0
        for card in cards:
            item = parse_card(card)
            if item and item["link"] not in seen_links:
                seen_links.add(item["link"])
                listings.append(item)
                nuevos += 1

        print(f"  [+] {os.path.basename(archivo)}: {nuevos} listados nuevos")

    return listings


def save_to_csv(listings: list[dict], filepath: str):
    if not listings:
        print(f"  [!] Nada que guardar en {filepath}")
        return

    fieldnames = listings[0].keys()
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(listings)

    print(f"  [✓] {len(listings)} listados guardados en {filepath}")


def main():
    if not os.path.isdir(CARPETA_RAIZ):
        print(f"[!] No encontré la carpeta '{CARPETA_RAIZ}'. Ajusta CARPETA_RAIZ en el script.")
        return

    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    # Detecta automáticamente las subcarpetas (una por municipio)
    subcarpetas = sorted(
        d for d in os.listdir(CARPETA_RAIZ)
        if os.path.isdir(os.path.join(CARPETA_RAIZ, d))
    )

    if not subcarpetas:
        print(f"[!] No encontré subcarpetas dentro de '{CARPETA_RAIZ}'.")
        return

    print(f"[*] Encontré {len(subcarpetas)} municipio(s): {', '.join(subcarpetas)}\n")

    todos_los_listados = []

    for municipio in subcarpetas:
        print(f"[*] Procesando: {municipio}")
        ruta_carpeta = os.path.join(CARPETA_RAIZ, municipio)

        listings = parse_folder(ruta_carpeta)

        # Agrega la columna de municipio a cada registro
        for item in listings:
            item["municipio"] = municipio

        # Nombre de archivo seguro (sin espacios ni acentos raros)
        nombre_archivo = municipio.strip().replace(" ", "_")
        ruta_csv = os.path.join(CARPETA_SALIDA, f"departamentos_{nombre_archivo}.csv")
        save_to_csv(listings, ruta_csv)

        todos_los_listados.extend(listings)
        print()

    # CSV combinado con todos los municipios juntos
    ruta_combinado = os.path.join(CARPETA_SALIDA, "departamentos_TODOS.csv")
    save_to_csv(todos_los_listados, ruta_combinado)

    print(f"\n[✓] Listo. Total general: {len(todos_los_listados)} departamentos en {len(subcarpetas)} municipios.")


if __name__ == "__main__":
    main()
