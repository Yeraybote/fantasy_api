from fastapi import FastAPI
from datetime import datetime
from playwright.async_api import async_playwright
from scrape_fantasy import get_change_for_player, SEARCH_SELECTOR, MARKET_URL

app = FastAPI()

@app.get("/scrape")
async def scrape(players: str):
    today = datetime.now().strftime("%Y-%m-%d")
    player_list = [p.strip() for p in players.split(",") if p.strip()]
    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(MARKET_URL, wait_until="networkidle")

        try:
            await page.click("text=ACEPTO")
        except:
            pass

        await page.click("text=Filtros")
        await page.wait_for_selector(SEARCH_SELECTOR, timeout=5000)

        for name in player_list:
            chg, price = await get_change_for_player(page, name)
            results.append({
                "fecha": today,
                "jugador": name,
                "cambio": chg,
                "precio": price
            })

        await browser.close()

    return {"data": results}
