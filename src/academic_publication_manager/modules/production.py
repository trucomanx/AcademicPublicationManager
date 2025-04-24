from datetime import datetime

fake_production = {
    "title": "New Publication",
    "subtitle": "",
    "authors": ["Author Name"],
    "year": datetime.now().year,
    "publicator_name": "Sample Journal",
    "url": "https://example.com",
    "type": "article",
    "language": "English",
    "version": 1,
    "serial_numbers": [{"type": "doi", "value": "10.1000/sample"}]
}
