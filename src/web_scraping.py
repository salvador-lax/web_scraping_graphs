import json
import os

from playwright.async_api import async_playwright
from src.constants import PROJECT_FOLDER


async def screenshot_graphs(municipioSelected: str = ""):
    """
    Takes screenshots of specific graphs for each municipality listed in a JSON file.
    This function performs the following steps:
    1. Parses a JSON file to get a list of municipalities.
    2. Uses Playwright to open a browser and navigate to a specific URL for each municipality.
    3. Hides certain elements on the page.
    4. Takes screenshots of specified graphs and saves them to a directory named after the municipality.
    The JSON file should have the following structure:
    {
        "municipios": [
            { "id": "...", "nombre": "..." },
            ...
        ]
    }
    The screenshots are saved in the "graph/{municipio_nombre}" directory.
    Raises:
        Exception: If any required elements are not found or if there are issues with the browser interaction.
    Note:
        This function requires the Playwright library and a JSON file named "municipios.json" in the "data" directory.
    """
    GRAPH_LIST = [
        "p03*dv003b002_A.A",
        "p03*dv003b003_A.B",
        "p03*dv003b004_A.C",
    ]

    ELEMENTS_TO_HIDE = [".datavizHeader>a", ".no-display.filter-axis"]

    with open(f"{PROJECT_FOLDER}/data/municipios.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    municipios = data.get("municipio", [])

    # ──► Filter if a specific municipio was requested
    if municipioSelected:
        municipios = [
            m
            for m in municipios
            if str(m.get("id")) == municipioSelected
            or m.get("nombre") == municipioSelected
        ]

    if not municipios:
        raise ValueError(f'No matching municipio found for "{municipioSelected}".')

    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, is_mobile=True
        )
        page = await context.new_page()

        for municipio in municipios:
            municipio_id = municipio.get("id")
            nombre = municipio.get("nombre")

            if not municipio_id or not nombre:
                continue

            nombre = nombre.replace("/", "-")

            url = f"https://atlasau.mitma.gob.es/#c=report&chapter=p03&report=r01&selgeo1=mun.{municipio_id}"

            await page.goto(url, wait_until="domcontentloaded")

            try:
                cookie_banner = page.locator(".cookie-notice-container")
                await cookie_banner.wait_for(state="visible", timeout=5000)
                await cookie_banner.evaluate(
                    'element => element.style.display = "none"'
                )
            except:
                pass  # Ignore if the cookie banner does not appear

            for graph in GRAPH_LIST:
                file_name = graph.split(".")[-1]
                element = page.locator(f"[id='{graph}'] article")

                await element.wait_for(state="visible", timeout=5000)

                for selector in ELEMENTS_TO_HIDE:
                    try:
                        element_to_hide = element.locator(selector)
                        await element_to_hide.wait_for(state="attached", timeout=5000)
                        await element_to_hide.evaluate(
                            'element => element.style.display = "none"'
                        )
                    except:
                        pass

                output_dir = f"{PROJECT_FOLDER}/graph/{nombre}"
                os.makedirs(output_dir, exist_ok=True)
                await element.screenshot(
                    animations="disabled", path=f"{output_dir}/{file_name}.png"
                )

        await browser.close()
