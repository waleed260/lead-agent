import gspread
from google.oauth2.service_account import Credentials
import json
import os
from dotenv import load_dotenv

load_dotenv()


def push_to_sheets(data_file="enriched.json"):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

    headers = [
        "Business Name", "Category", "Phone", "Email", "Website",
        "Address", "Instagram", "Facebook", "LinkedIn", "Twitter", "Founder"
    ]
    sheet.clear()
    sheet.append_row(headers)

    sheet.format("A1:K1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.8}
    })

    with open(data_file) as f:
        businesses = json.load(f)

    rows = []
    for biz in businesses:
        rows.append([
            biz.get("name", ""),
            biz.get("category", ""),
            biz.get("phone", ""),
            biz.get("email", ""),
            biz.get("website", ""),
            biz.get("address", ""),
            biz.get("instagram", ""),
            biz.get("facebook", ""),
            biz.get("linkedin", ""),
            biz.get("twitter", ""),
            biz.get("founder", "")
        ])

    sheet.append_rows(rows)
    print(f"✅ Pushed {len(rows)} rows to Google Sheets!")


if __name__ == "__main__":
    push_to_sheets()
