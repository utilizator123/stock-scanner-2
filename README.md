# US Stock Momentum Scanner (MVP)

## Publicare pe Render
1. Încarcă toate fișierele în repository-ul GitHub.
2. În Render: New + -> Web Service -> conectează repository-ul.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Adaugă Environment Variable `FMP_API_KEY` cu cheia ta FMP.
6. Deploy. Render va afișa URL-ul public.

## Rulare locală (Windows)
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:FMP_API_KEY="CHEIA_TA"
uvicorn app:app --reload
```
Apoi deschide http://127.0.0.1:8000

## Atenție
Acesta este un MVP demonstrativ, nu un sistem de tranzacționare validat. Necesită un API key FMP și un plan care permite endpoint-urile folosite. Scanează cel mult 500 de simboluri per cerere; în mod strict exclude simbolurile pentru care lipsesc date. Indicatorii sunt calculați din date daily inclusiv pentru utilizare intraday; nu este backtestat și nu trebuie folosit singur pentru decizii financiare.
