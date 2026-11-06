"""Abre o HTML do GitEvo, valida os gráficos e captura Function return type."""

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / "imagens" / "flask-tipos-retorno.png"
    output.parent.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=2)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.goto((ROOT / "relatorios" / "flask.html").as_uri(), wait_until="networkidle")
        page.wait_for_function("""() => {
            const data = JSON.parse(document.getElementById('jsonData').textContent);
            return typeof Chart !== 'undefined' && Object.keys(Chart.instances).length === data.length;
        }""")
        info = page.evaluate("""() => {
            const data = JSON.parse(document.getElementById('jsonData').textContent);
            const index = data.findIndex(c => c.title === 'Function return type' && c.type === 'line');
            if (index < 0) throw new Error('Gráfico de evolução não encontrado');
            for (const chart of Object.values(Chart.instances)) {
                chart.stop();
                chart.update('none');
                if (chart.width <= 0 || chart.height <= 0) throw new Error('Gráfico vazio');
            }
            return {index, charts: data.length, data: data[index]};
        }""")
        if errors:
            raise RuntimeError("Erros ao abrir o relatório: " + "; ".join(errors))
        page.locator(f"#chart-{info['index']}").screenshot(path=str(output))
        print(f"{info['charts']} gráficos renderizados sem erros JavaScript.")
        print(f"Imagem: {output}")
        browser.close()


if __name__ == "__main__":
    main()
