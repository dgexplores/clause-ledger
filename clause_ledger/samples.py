SAMPLES = [
    {"id": "balanced", "title": "Northstar · standard services", "text": """SYNTHETIC SUPPLIER AGREEMENT — NOT A REAL CONTRACT
Supplier: Northstar Systems (fictional)
Customer: Arbor Studio (fictional)
Payment terms: NET 30 days from invoice receipt.
Uptime commitment: 99.9% per calendar month.
Breach notification: within 48 hours of discovery.
Either party may terminate on 30 days written notice.
The customer may audit service records once each year.
This document is a demonstration fixture for software testing."""},
    {"id": "exceptions", "title": "Cobalt · exceptions to review", "text": """SYNTHETIC SUPPLIER AGREEMENT — NOT A REAL CONTRACT
Supplier: Cobalt Labs (fictional)
Customer: Arbor Studio (fictional)
Payment terms: NET 90 days from invoice receipt.
Availability target: 98.5% per calendar month.
Breach notification: within 120 hours of discovery.
Either party may terminate on 60 days written notice.
No audit wording is included in this synthetic fixture.
The reviewer should request changes before accepting the sample."""},
    {"id": "conflict", "title": "Meridian · conflicting terms", "text": """SYNTHETIC SUPPLIER AGREEMENT — NOT A REAL CONTRACT
Supplier: Meridian Support (fictional)
Main schedule: Payment terms: NET 30 days from invoice receipt.
Appendix: Payment terms: NET 90 days from invoice receipt.
Uptime commitment: 99.8% per calendar month.
Breach notification: within 24 hours of discovery.
The customer may terminate on 15 days written notice.
The customer may audit operational records annually.
The payment schedules intentionally conflict for reviewer investigation."""},
]
