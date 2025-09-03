# scrape_fantasy.py
# Scrap de mercado Analítica Fantasy.
# Cada ejecución genera (o reemplaza) una hoja en Excel con la fecha del día,
# y actualiza una hoja "Resumen" con el total de cambios de cada día.

import asyncio
import re
from datetime import datetime
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright

MARKET_URL = "https://www.analiticafantasy.com/fantasy-la-liga/mercado"

# -------- SELECTORES ----------
SEARCH_SELECTOR = "div.MuiInputBase-root input[type='text']"
CARD_SELECTOR   = "section:has-text('€'), article:has-text('€')"
PRICE_SELECTOR  = "xpath=(.//p[contains(@class,'MuiTypography-body1')])[1]"
CHANGE_SELECTOR = "xpath=(.//p[contains(@class,'MuiTypography-body1')])[2]"
# --------------------------------

EXCEL_PATH = Path("fantasy_tracker.xlsx")
PLAYERS_PATH = Path("players.txt")

def parse_euro(text: str) -> int:
    """Convierte '1.730.893 €' -> 1730893 ; '-818.308 €' -> -818308"""
    if not text:
        return 0
    t = text.replace("€", "").strip()
    m = re.search(r"[-+]?\d[\d\.]*", t)
    if not m:
        return 0
    num = m.group().replace(".", "")
    return int(num)

async def get_change_for_player(page, player_name: str):
    # Limpia el buscador antes de escribir
    await page.click(SEARCH_SELECTOR)
    await page.fill(SEARCH_SELECTOR, "")
    await page.type(SEARCH_SELECTOR, player_name)
    await page.wait_for_timeout(300)

    el = page.locator(f"text={player_name}").first
    if await el.count() == 0:
        print(f"⚠️ No encontrado: {player_name}")
        return None, None

    card = el.locator("..").locator("..")
    if await card.count() == 0:
        card = page.locator(CARD_SELECTOR).first

    # Extrae cambio y precio
    change_el = card.locator(CHANGE_SELECTOR).first
    price_el  = card.locator(PRICE_SELECTOR).first

    change = None
    price = None
    if await change_el.count() > 0:
        change = parse_euro(await change_el.text_content())
    if await price_el.count() > 0:
        price = parse_euro(await price_el.text_content())

    return change, price

async def run():
    today = datetime.now().strftime("%Y-%m-%d")
    players = [p.strip() for p in PLAYERS_PATH.read_text(encoding="utf-8").splitlines() if p.strip()]

    # DataFrame inicial del día
    raw = pd.DataFrame(columns=["Fecha", "Jugador", "Cambio (€)", "Precio actual (€)"])

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=400)
        page = await browser.new_page()
        await page.goto(MARKET_URL, wait_until="networkidle")
        await page.wait_for_timeout(500)

        # 1️⃣ Aceptar cookies
        try:
            await page.click("text=ACEPTO")
            await page.wait_for_timeout(500)
        except Exception:
            pass

        # 2️⃣ Abrir filtros
        try:
            await page.click("text=Filtros")
        except Exception:
            print("❌ No encontré el botón 'Filtros'.")
            await browser.close()
            return

        # 3️⃣ Espera al buscador
        try:
            await page.wait_for_selector(SEARCH_SELECTOR, timeout=5000)
        except Exception:
            print("❌ No se encontró el input de búsqueda.")
            await browser.close()
            return

        # 4️⃣ Procesar jugadores
        daily_changes = []
        for name in players:
            chg, price = await get_change_for_player(page, name)
            raw.loc[len(raw)] = [today, name, chg if chg is not None else "", price if price is not None else ""]
            if chg is not None:
                daily_changes.append(chg)

        await browser.close()

    # 5️⃣ Resumen del día
    total_change_today = sum(daily_changes)
    raw.loc[len(raw)] = [today, "TOTAL CAMBIO DÍA", total_change_today, ""]

    # 6️⃣ Guardar Excel -> hoja del día (se reemplaza si ya existe)
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode="a" if EXCEL_PATH.exists() else "w", if_sheet_exists="replace") as writer:
        raw.to_excel(writer, sheet_name=today, index=False)

        # Actualizar hoja Resumen
        try:
            resumen = pd.read_excel(EXCEL_PATH, sheet_name="Resumen")
        except Exception:
            resumen = pd.DataFrame(columns=["Fecha", "Total cambio del día (€)"])

        # Eliminar fila existente para este día (si la hay)
        resumen = resumen[resumen["Fecha"] != today]

        # Añadir fila actual
        resumen.loc[len(resumen)] = [today, total_change_today]

        # Guardar Resumen actualizado
        resumen.to_excel(writer, sheet_name="Resumen", index=False)

    print(f"✅ OK - Datos del día guardados en hoja '{today}' y actualizado Resumen.")

if __name__ == "__main__":
    asyncio.run(run())
